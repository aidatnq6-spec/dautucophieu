"""Monthly P/E and P/B history for the Định giá charts, on the same figures and rule as the weekly series (valuation/weekly.py).

Each month's last adjusted close × today's share count over the trailing four quarters' profit (the latest annual report when
those quarters are not all there) or the latest equity, each figure counted from the day its report is out. Tickers with VNDirect
statements use their parent profit and equity and VNDirect's listing days (valuation/sources.py). The band statistics (median,
population standard deviation) cover the whole series.
"""

import statistics
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .reference import metrics
from .weekly import last_close_by, multiples_at, published_from

_Q2 = Decimal("0.01")


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else str(value.quantize(_Q2, ROUND_HALF_UP))


def _series(points: list[dict]) -> dict:
    values = [Decimal(p["value"]) for p in points if p["value"] is not None]
    if not values:
        return {"points": points, "median": None, "sd": None, "latest": None}
    sd = Decimal(str(statistics.pstdev(float(v) for v in values)))
    return {"points": points, "median": _fmt(Decimal(str(statistics.median(values)))), "sd": _fmt(sd), "latest": _fmt(values[-1])}


def _month(p: dict) -> dict:
    return {"month": p["date"][:7], "value": p["value"], "year": p["period"], "basis": p["basis"]}


def monthly_multiples(record: dict | None, points, *, today: date, shares: int | None = None, published=None) -> dict:
    empty = {"pe": _series([]), "pb": _series([]), "shares": None, "from": None, "to": None}
    if shares is None:
        m = metrics(record, today=today, year_end_prices={}) if record and record.get("years") else None
        shares = m["shares"] if m else None
    if shares is None or not record or not (record.get("years") or record.get("quarters")):
        return {**empty, "reason": "Chưa có báo cáo tài chính"}
    pe, pb, _ = multiples_at(record, last_close_by(points, lambda d: (d.year, d.month)), shares=shares, pub=published or published_from)
    if not pe and not pb:
        return {**empty, "shares": int(shares), "reason": "Chưa có lịch sử giá"}
    months = [p["date"][:7] for p in pe + pb]
    return {"pe": _series([_month(p) for p in pe]), "pb": _series([_month(p) for p in pb]), "shares": int(shares),
            "from": min(months), "to": max(months), "reason": None}
