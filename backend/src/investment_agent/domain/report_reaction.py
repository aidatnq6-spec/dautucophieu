"""Phản ứng giá sau báo cáo: how the price moved after each quarterly report came out, set beside the profit change it reported.

The report day is the day VNDirect first held the quarter's figures; it counts only when it falls within 120 days after the
quarter ended (the older quarters were loaded later in bulk and carry that later day, so they have none). The base is the last
close before the report day; the moves are 5 and 20 sessions on, alone and less VN-Index's move over the same sessions. Adjusted
closes. A missing price or day leaves the cell blank. Not advice: it shows what happened, not what will."""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

_Q4 = Decimal("0.0001")
REPORT_WINDOW_DAYS = 120
HORIZONS = (5, 20)
_QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def _r(v: Decimal | None) -> str | None:
    return str(v.quantize(_Q4, ROUND_HALF_UP)) if v is not None else None


def _d(v) -> Decimal | None:
    try:
        return Decimal(str(v)) if v is not None else None
    except ArithmeticError:
        return None


def _end(period: str) -> date:
    y, n = (int(x) for x in period.split("-Q"))
    return date(y, *_QUARTER_END[n])


def _day(t) -> date:
    return t.date() if isinstance(t, datetime) else t


def reaction(quarters: dict, created: dict, closes: list, index: list, *, n: int = 8) -> dict:
    """closes, index: [(datetime or date, close)] oldest first."""
    days = [_day(t) for t, _ in closes]
    values = [Decimal(str(v)) for _, v in closes]
    index_at = {_day(t): Decimal(str(v)) for t, v in index}
    rows = []
    for p in sorted(quarters)[-n:]:
        y, q = p.split("-Q")
        ago = quarters.get(f"{int(y) - 1}-Q{q}", {})
        profit, profit_ago = _d(quarters[p].get("npat_parent")), _d(ago.get("npat_parent"))
        turn = None
        if profit is not None and profit_ago is not None:
            turn = "to_profit" if profit_ago <= 0 < profit else "to_loss" if profit < 0 <= profit_ago else None
        row = {"quarter": p, "report_day": None, "base_day": None, "reason": None, "profit_turn": turn,
               "profit_yoy": _r(profit / profit_ago - 1) if profit is not None and profit_ago is not None and profit_ago > 0 else None,
               **{f"{k}_{h}": None for h in HORIZONS for k in ("after", "index", "excess")}}
        raw = created.get(p)
        day = date.fromisoformat(raw[:10]) if raw else None
        if day is None or not _end(p) < day <= _end(p) + timedelta(days=REPORT_WINDOW_DAYS):
            rows.append({**row, "reason": "no_report_day"})
            continue
        row["report_day"] = day.isoformat()
        base = max((i for i, d in enumerate(days) if d < day), default=None)
        if base is None or days[base] < day - timedelta(days=10):
            rows.append({**row, "reason": "no_prices"})
            continue
        row["base_day"] = days[base].isoformat()
        for h in HORIZONS:
            if base + h >= len(values):
                continue
            move = values[base + h] / values[base] - 1
            row[f"after_{h}"] = _r(move)
            i0, i1 = index_at.get(days[base]), index_at.get(days[base + h])
            if i0 and i1:
                row[f"index_{h}"] = _r(i1 / i0 - 1)
                row[f"excess_{h}"] = _r(move - (i1 / i0 - 1))
        rows.append(row)
    return {"rows": rows, "summary": summary(rows)}


def summary(rows: list[dict]) -> dict:
    """Over the quarters with both a profit change and a 20-session move: profit up but price down ("good news sold"), profit down
    but price up ("bad news bought"), and the rest."""
    def profit_sign(r):
        if r.get("profit_turn") == "to_profit":
            return 1
        if r.get("profit_turn") == "to_loss":
            return -1
        return None if r.get("profit_yoy") is None else (1 if Decimal(r["profit_yoy"]) > 0 else -1 if Decimal(r["profit_yoy"]) < 0 else 0)
    pairs = [(profit_sign(r), Decimal(r["after_20"])) for r in rows if r.get("after_20") is not None]
    pairs = [(s, m) for s, m in pairs if s is not None]
    good_sold = sum(1 for s, m in pairs if s > 0 and m < 0)
    bad_bought = sum(1 for s, m in pairs if s < 0 and m > 0)
    return {"compared": len(pairs), "good_sold": good_sold, "bad_bought": bad_bought, "same_way": len(pairs) - good_sold - bad_bought}
