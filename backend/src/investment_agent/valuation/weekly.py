"""Weekly P/E (trailing four quarters) and P/B, each week priced with only the statements already published that week.

Publication rule (docs/decisions/market-rules.md): year Y counts from 1 April Y+1, as in the monthly chart; a quarter from
45 days after it ends, the latest a listed company may publish it (20 days, or 45 for a reviewed report, Thông tư
96/2020/TT-BTC Điều 14). Actual dates are not in the free tier, so the latest deadline is used to avoid figures before
they were out.

The free tier keeps only the latest eight periods, so each week takes the newest figures the store has:
- P/E: the four quarters to the latest quarter out ("4 quý") when all four are stored, otherwise the latest annual
  report out ("năm"); the quarters of that window not stored are named, never filled in. When the latest quarter out
  is the fourth of the annual report's year, both are the same twelve months and nothing is missing.
- P/B: equity at the end of the latest quarter out ("quý") when stored, otherwise at the end of the latest year out.
Price is the week's last adjusted close × today's share count, the basis of the monthly chart, so bonus issues and splits
do not distort the line. A loss gives no P/E; a week with neither figure gives no point.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .reference import _d, metrics

_Q2 = Decimal("0.01")
QUARTER_LAG_DAYS = 45
_QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _quarter(year: int, q: int) -> str:
    return f"{year}-Q{q}"


def _split(period: str) -> tuple[int, int]:
    return int(period[:4]), int(period[-1])


def published_from(period: str) -> date:
    """First day a period's report counts as out: 1 April of the next year for a year, 45 days after the end for a quarter."""
    if "-Q" not in period:
        return date(int(period) + 1, 4, 1)
    year, q = _split(period)
    return date(year, *_QUARTER_END[q]) + timedelta(days=QUARTER_LAG_DAYS)


def _latest_quarter_out(day: date, pub=published_from) -> str:
    year, q = day.year, (day.month - 1) // 3 + 1
    while pub(_quarter(year, q)) > day:
        year, q = (year, q - 1) if q > 1 else (year - 1, 4)
    return _quarter(year, q)


def _window(quarter: str) -> list[str]:
    year, q = _split(quarter)
    out = []
    for _ in range(4):
        out.append(_quarter(year, q))
        year, q = (year, q - 1) if q > 1 else (year - 1, 4)
    return out[::-1]


def _latest_year_out(years: dict, field: str, day: date, pub=published_from) -> str | None:
    usable = [y for y in sorted(years) if _d(years[y].get(field)) is not None and pub(y) <= day]
    return usable[-1] if usable else None


def _profit(record: dict, day: date, pub=published_from) -> dict | None:
    quarters, latest = record.get("quarters", {}), _latest_quarter_out(day, pub)
    window = _window(latest)
    missing = [q for q in window if _d(quarters.get(q, {}).get("npat")) is None]
    if not missing:
        return {"basis": "4 quý", "period": latest, "denominator": sum(_d(quarters[q]["npat"]) for q in window), "missing": []}
    year = _latest_year_out(record.get("years", {}), "npat", day, pub)
    if year is None:
        return None
    return {"basis": "năm", "period": year, "denominator": _d(record["years"][year]["npat"]),
            "missing": [] if latest == _quarter(int(year), 4) else missing}


def _equity(record: dict, day: date, pub=published_from) -> dict | None:
    quarters, latest = record.get("quarters", {}), _latest_quarter_out(day, pub)
    equity = _d(quarters.get(latest, {}).get("equity"))
    if equity is not None:
        return {"basis": "quý", "period": latest, "denominator": equity, "missing": []}
    year = _latest_year_out(record.get("years", {}), "equity", day, pub)
    if year is None:
        return None
    return {"basis": "năm", "period": year, "denominator": _d(record["years"][year]["equity"]),
            "missing": [] if latest == _quarter(int(year), 4) else [latest]}


def _point(day: date, price: Decimal, shares: Decimal, base: dict) -> dict:
    d = base["denominator"]
    value = (price * shares / d).quantize(_Q2, ROUND_HALF_UP) if d > 0 else None
    return {"date": day.isoformat(), "close": _plain(price), "value": None if value is None else str(value),
            "basis": base["basis"], "period": base["period"], "denominator": _plain(d), "missing": base["missing"]}


def weekly_multiples(record: dict | None, points, *, today: date, shares: int | None = None, published=None) -> dict:
    """`published` maps a period to the day its report counts as out (default: the fixed rule); `shares` is today's share count
    (default: the reference valuation's, from the same record)."""
    empty = {"pe": {"points": []}, "pb": {"points": []}, "shares": None, "from": None, "to": None, "missing_quarters": []}
    pub = published or published_from
    if shares is None:
        m = metrics(record, today=today, year_end_prices={}) if record and record.get("years") else None
        shares = m["shares"] if m else None
    if shares is None or not record or not (record.get("years") or record.get("quarters")):
        return {**empty, "reason": "Chưa có báo cáo tài chính"}
    week_close: dict[tuple[int, int], tuple[date, Decimal]] = {}
    for t, close in points:
        price = Decimal(str(close)) * 1000
        if price > 0:  # the source sometimes returns 0 for very old sessions
            week_close[t.date().isocalendar()[:2]] = (t.date(), price)  # last close of the week wins
    shares, pe, pb, missing = Decimal(shares), [], [], set()
    for _, (day, price) in sorted(week_close.items()):
        profit, equity = _profit(record, day, pub), _equity(record, day, pub)
        if profit is None and equity is None:
            continue
        if profit is not None:
            pe.append(_point(day, price, shares, profit))
            missing.update(profit["missing"])
        if equity is not None:
            pb.append(_point(day, price, shares, equity))
            missing.update(equity["missing"])
    days = [p["date"] for p in pe + pb]
    if not days:
        return {**empty, "shares": int(shares), "reason": "Chưa có lịch sử giá"}
    return {"pe": {"points": pe}, "pb": {"points": pb}, "shares": int(shares), "from": min(days), "to": max(days),
            "missing_quarters": sorted(missing), "reason": None}
