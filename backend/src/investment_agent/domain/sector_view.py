"""Toàn ngành: a sector's watched tickers side by side.

Bản đồ nhiệt: for each of the last quarters, each ticker's parent profit against the same quarter a year before, its cash from
operations, and its borrowing against a year before; the sector's own cell adds up the tickers that have the figures on both
sides. A year-ago loss is no base for a growth rate: the cell says the company turned to profit (or to a loss) instead.

Định giá ngành: the median P/B of the sector's tickers each month (a median is not pulled by one very large ticker, as an
average weighted by size would be), how the latest month ranks in that history, and each ticker's P/B against the sector median
and against its own lowest month of the five years before. A month with fewer than three tickers has no median. Nothing is filled
in. Readings, not advice."""

import re
import statistics
import unicodedata
from decimal import ROUND_HALF_UP, Decimal

_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")
MIN_TICKERS = 3
OWN_LOW_MONTHS = 60


def sector_key(name: str) -> str:
    plain = unicodedata.normalize("NFD", name.replace("Đ", "D").replace("đ", "d"))
    plain = "".join(c for c in plain if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def _d(v) -> Decimal | None:
    try:
        return Decimal(str(v)) if v is not None else None
    except ArithmeticError:
        return None


def _r(v: Decimal | None, q: Decimal = _Q4) -> str | None:
    return str(v.quantize(q, ROUND_HALF_UP)) if v is not None else None


def _year_ago(period: str) -> str:
    y, n = period.split("-Q")
    return f"{int(y) - 1}-Q{n}"


def _debt(q: dict) -> Decimal | None:
    st, lt = _d((q or {}).get("st_debt")), _d((q or {}).get("lt_debt"))
    return st + lt if st is not None and lt is not None else None


def _growth(now: Decimal | None, before: Decimal | None) -> Decimal | None:
    return now / before - 1 if now is not None and before is not None and before > 0 else None


def heatmap(records: dict[str, dict], n: int = 8) -> dict:
    periods = sorted({p for quarters in records.values() for p in quarters})[-n:]
    rows = []
    for symbol in sorted(records):
        quarters, cells = records[symbol], []
        for p in periods:
            now, ago = quarters.get(p, {}), quarters.get(_year_ago(p), {})
            profit, profit_ago = _d(now.get("npat_parent")), _d(ago.get("npat_parent"))
            turn = None
            if profit is not None and profit_ago is not None:
                turn = "to_profit" if profit_ago <= 0 < profit else "to_loss" if profit < 0 <= profit_ago else None
            cells.append({"quarter": p, "profit_yoy": _r(_growth(profit, profit_ago)), "profit_turn": turn, "cfo": now.get("cfo"),
                          "debt_yoy": _r(_growth(_debt(now), _debt(ago)))})
        rows.append({"symbol": symbol, "cells": cells})
    total = []
    for p in periods:
        pairs = [(_d(r.get(p, {}).get("npat_parent")), _d(r.get(_year_ago(p), {}).get("npat_parent"))) for r in records.values()]
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None and b > 0]
        cfos = [c for c in (_d(r.get(p, {}).get("cfo")) for r in records.values()) if c is not None]
        debts = [(_debt(r.get(p, {})), _debt(r.get(_year_ago(p), {}))) for r in records.values()]
        debts = [(a, b) for a, b in debts if a is not None and b is not None]
        total.append({"quarter": p, "profit_yoy": _r(_growth(sum(a for a, _ in pairs), sum(b for _, b in pairs))) if pairs else None,
                      "profit_count": len(pairs), "cfo": format(sum(cfos), "f") if cfos else None, "cfo_count": len(cfos),
                      "debt_yoy": _r(_growth(sum(a for a, _ in debts), sum(b for _, b in debts))) if debts else None, "debt_count": len(debts)})
    return {"quarters": periods, "rows": rows, "total": total}


def valuation(series: dict[str, list[tuple[str, str | None]]]) -> dict:
    """series: symbol → [(month "YYYY-MM", P/B or None)], oldest first."""
    by_month: dict[str, dict[str, Decimal]] = {}
    for symbol, points in series.items():
        for month, value in points:
            v = _d(value)
            if v is not None and v > 0:
                by_month.setdefault(month, {})[symbol] = v
    median = []
    for month in sorted(by_month):
        values = list(by_month[month].values())
        median.append({"month": month, "value": _r(Decimal(str(statistics.median(values))), _Q2) if len(values) >= MIN_TICKERS else None,
                       "count": len(values)})
    known = [m for m in median if m["value"] is not None]
    now = None
    if known:
        last = known[-1]
        value, earlier = Decimal(last["value"]), [m for m in known[:-1]]
        lower = [m for m in earlier if Decimal(m["value"]) < value]
        now = {**last, "lowest_since": lower[-1]["month"] if lower else None,
               "rank": _r(Decimal(len(lower)) / Decimal(len(earlier))) if earlier else None, "months": len(known)}
    tickers = []
    if now:
        sector_median = Decimal(now["value"])
        for symbol, points in series.items():
            own = [(m, _d(v)) for m, v in points if _d(v) is not None and _d(v) > 0]
            if not own or own[-1][0] != now["month"]:
                continue
            pb = own[-1][1]
            before = [v for _, v in own[:-1]][-OWN_LOW_MONTHS:]
            low = min(before) if before else None
            tickers.append({"symbol": symbol, "pb": _r(pb, _Q2), "to_median": _r(pb / sector_median), "own_low": _r(low, _Q2) if low is not None else None,
                            "below_own_low": (pb <= low) if low is not None else None, "own_months": len(before)})
        tickers.sort(key=lambda t: Decimal(t["to_median"]))
    return {"median": median, "now": now, "tickers": tickers}
