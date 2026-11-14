"""Rebuilds the stored daily closes of VN-Index and VN30 in points.

The series held before 10/2022 came from an old source that quoted the indices in thousand points rounded to 0.01 (1.47 for VN-Index
at 1,473.37 on 12/11/2021): ratios across that join were wrong, and closes were too coarse to rescale. VNDirect's vnmarket_prices
(the source of the daily refresh) has the indices in points from 24/08/2017; CafeF's price history (cafef.vn/du-lieu, robots.txt
allows all, checked 14/11/2026) has them in points from the first session. The two agreed to the point on every overlapping day
checked (2018). The older years come from CafeF, the rest from VNDirect.

Nothing changes unless the sources agree where both have closes and every close is at least 100 points (VN-Index began at 100 in
2000; VN30 at 500 in 2012). The old file is kept by the caller before the series is replaced.
"""

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Callable

VND_URL = ("https://api-finfo.vndirect.com.vn/v4/vnmarket_prices?q=code:{symbol}~date:gte:2000-01-01~date:lte:{end}&size=9999"
           "&fields=code,date,close")
CAFEF_URL = ("https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/PriceHistory.ashx?Symbol={symbol}&StartDate={start}&EndDate={end}"
             "&PageIndex={page}&PageSize=30")
CAFEF_SYMBOL = {"VNINDEX": "VNINDEX", "VN30": "VN30INDEX"}
FIRST_YEAR = {"VNINDEX": 2000, "VN30": 2012}
FLOOR = Decimal(100)
AGREE = Decimal("0.0005")  # 0.05%
CHECK_DAYS = 120  # the overlap compared after VNDirect's first day
PAGE = 30


def _us(d: date) -> str:
    return d.strftime("%m/%d/%Y")


def _decimal(value) -> Decimal | None:
    return Decimal(str(value)) if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else None


def vndirect_closes(index: str, get: Callable[[str], str], today: date) -> dict[date, Decimal]:
    rows = json.loads(get(VND_URL.format(symbol=index, end=today.isoformat()))).get("data") or []
    return {date.fromisoformat(r["date"][:10]): v for r in rows if str(r.get("code") or index).upper() == index and (v := _decimal(r.get("close")))}


def cafef_closes(index: str, start: date, end: date, get: Callable[[str], str], sleep: Callable[[float], None]) -> dict[date, Decimal]:
    """One calendar year a request window (CafeF serves at most about a year), 30 rows a page."""
    out: dict[date, Decimal] = {}
    year = start.year
    while year <= end.year:
        lo, hi, page = max(start, date(year, 1, 1)), min(end, date(year, 12, 31)), 1
        while True:
            answer = json.loads(get(CAFEF_URL.format(symbol=CAFEF_SYMBOL[index], start=_us(lo), end=_us(hi), page=page)))
            data = answer.get("Data") or {}
            rows = data.get("Data") or []
            for r in rows:
                d, m, y = str(r.get("Ngay") or "").split("/")
                day = date(int(y), int(m), int(d))
                if lo <= day <= hi and (v := _decimal(r.get("GiaDongCua"))):
                    out[day] = v
            sleep(0.4)
            if len(rows) < PAGE or page * PAGE >= int(data.get("TotalCount") or 0):
                break
            page += 1
        year += 1
    return out


def rebuild_index_history(store, index: str, *, get: Callable[[str], str], today: date, sleep: Callable[[float], None]) -> dict:
    """Replaces store's "<index>-1d" with closes in points; returns what was done, or an error with the series left as it was."""
    index, key = index.upper(), f"{index.upper()}-1d"
    error = lambda reason: {"status": "error", "reason": reason, "index": index}  # noqa: E731
    vnd = vndirect_closes(index, get, today)
    if not vnd:
        return error("vndirect_empty")
    first = min(vnd)
    check = cafef_closes(index, first, first + timedelta(days=CHECK_DAYS), get, sleep)
    overlap = [d for d in check if d in vnd]
    if len(overlap) < 20:
        return error("no_overlap")
    if any(abs(check[d] / vnd[d] - 1) > AGREE for d in overlap):
        return error("sources_disagree")
    older = cafef_closes(index, date(FIRST_YEAR[index], 1, 1), first - timedelta(days=1), get, sleep)
    merged = {**older, **vnd}
    if any(v < FLOOR for v in merged.values()):
        return error("unit")
    held = {date.fromisoformat(t[:10]): Decimal(v) for t, v in store.points(key)}
    coarse = [d for d, v in held.items() if v < FLOOR and d in merged and abs((merged[d] / 1000).quantize(Decimal("0.01")) - v) > Decimal("0.01")]
    held_only = [d for d in held if d not in merged]
    store.replace(key, [(datetime.combine(d, datetime.min.time()), format(v, "f")) for d, v in sorted(merged.items())])
    return {"status": "ok", "index": index, "days": len(merged), "first": min(merged).isoformat(), "vndirect_from": first.isoformat(),
            "cafef_days": len(older), "checked_days": len(overlap), "held_days": len(held), "held_only_days": len(held_only),
            "coarse_mismatch": len(coarse)}
