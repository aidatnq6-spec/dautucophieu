"""Monthly P/E and P/B history for the Định giá charts, computed locally from stored statements and prices.

Same basis as the P/E-history method in reference.py: the adjusted month-end close × today's share count over the
profit (or equity) of the latest fiscal year already published, so bonus issues and splits do not distort the line.
Year Y figures are taken as published from 1 April Y+1 (annual reports are due by the end of the first quarter).
"""

import statistics
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .reference import _d, metrics

_Q2 = Decimal("0.01")


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else str(value.quantize(_Q2, ROUND_HALF_UP))


def _published_year(years: list[str], month_end: date) -> str | None:
    usable = [y for y in years if date(int(y) + 1, 4, 1) <= month_end]
    return usable[-1] if usable else None


def _series(points: list[dict]) -> dict:
    values = [Decimal(p["value"]) for p in points if p["value"] is not None]
    if not values:
        return {"points": points, "median": None, "sd": None, "latest": None}
    sd = Decimal(str(statistics.pstdev(float(v) for v in values)))
    return {"points": points, "median": _fmt(Decimal(str(statistics.median(values)))), "sd": _fmt(sd), "latest": _fmt(values[-1])}


def monthly_multiples(record: dict | None, points, *, today: date) -> dict:
    empty = {"pe": _series([]), "pb": _series([]), "shares": None, "from": None, "to": None}
    m = metrics(record, today=today, year_end_prices={}) if record and record.get("years") else None
    if m is None:
        return {**empty, "reason": "Chưa có báo cáo tài chính"}
    month_close: dict[str, tuple[date, Decimal]] = {}
    for t, close in points:
        month_close[t.strftime("%Y-%m")] = (t.date(), Decimal(str(close)) * 1000)  # last close of the month wins
    years, shares = sorted(record["years"]), m["shares"]
    pe, pb = [], []
    for month, (day, price) in sorted(month_close.items()):
        year = _published_year(years, day)
        if year is None:
            continue
        npat, equity = _d(record["years"][year].get("npat")), _d(record["years"][year].get("equity"))
        pe.append({"month": month, "value": _fmt(price * shares / npat) if npat and npat > 0 else None, "year": year})
        pb.append({"month": month, "value": _fmt(price * shares / equity) if equity and equity > 0 else None, "year": year})
    if not pe:
        return {**empty, "shares": int(shares), "reason": "Chưa có lịch sử giá"}
    return {"pe": _series(pe), "pb": _series(pb), "shares": int(shares), "from": pe[0]["month"], "to": pe[-1]["month"], "reason": None}
