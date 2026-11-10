"""Mùa báo cáo: the watched tickers' results for the latest quarter out, from their stored statements (public figures). Per ticker: profit against
the same quarter a year before, the quarter before and the year so far; the owner's plan and forecast; how much of a year this quarter usually
carries. Per sector: the year so far, how much the biggest contributor carried, and the growth without it. Profit against cash from operations
for the year so far. A comparison missing a figure is None, never filled in. Not advice."""

from decimal import ROUND_HALF_UP, Decimal

_Q4 = Decimal("0.0001")
CASH_ABOVE = Decimal(2)  # cash from operations at least twice the profit: worth reading the notes (the application's own line)


def _d(v) -> Decimal | None:
    try:
        return Decimal(str(v)) if v is not None else None
    except ArithmeticError:
        return None


def _s(v: Decimal | None) -> str | None:
    return format(v, "f") if v is not None else None


def _r(v: Decimal | None) -> str | None:
    return str(v.quantize(_Q4, ROUND_HALF_UP)) if v is not None else None


def _growth(now: Decimal | None, before: Decimal | None) -> Decimal | None:
    return now / before - 1 if now is not None and before is not None and before > 0 else None


def _split(q: str) -> tuple[int, int]:
    y, n = q.split("-Q")
    return int(y), int(n)


def _prev(q: str) -> str:
    y, n = _split(q)
    return f"{y}-Q{n - 1}" if n > 1 else f"{y - 1}-Q4"


def target_quarter(records: dict[str, dict]) -> str | None:
    """The latest quarter any watched ticker has: the season under way."""
    return max((q for quarters in records.values() for q in quarters), default=None)


def _value(quarters: dict, q: str, field: str = "npat_parent") -> Decimal | None:
    return _d((quarters.get(q) or {}).get(field))


def _year_so_far(quarters: dict, q: str, field: str = "npat_parent") -> Decimal | None:
    y, n = _split(q)
    parts = [_value(quarters, f"{y}-Q{k}", field) for k in range(1, n + 1)]
    return sum(parts) if None not in parts else None


def _seasonal_share(quarters: dict, q: str) -> Decimal | None:
    """This quarter's average share of a full year's profit over up to three earlier full, profitable years."""
    y, n = _split(q)
    shares = []
    for year in range(y - 3, y):
        parts = [_value(quarters, f"{year}-Q{k}") for k in range(1, 5)]
        if None not in parts and sum(parts) > 0:
            shares.append(parts[n - 1] / sum(parts))
    return sum(shares) / len(shares) if shares else None


def season_rows(records: dict[str, dict], sectors: dict[str, str], *, target: str, held: set[str], plans: dict | None = None,
                forecasts: dict | None = None, reviews: dict | None = None) -> list[dict]:
    """plans: symbol → {"ratio", "label"} for the year of `target`; forecasts: symbol → the owner's forecast parent profit for `target`;
    reviews: symbol → the owner's verdict recorded after `target`."""
    plans, forecasts, reviews = plans or {}, forecasts or {}, reviews or {}
    y, n = _split(target)
    year_ago = f"{y - 1}-Q{n}"
    out = []
    for symbol in sorted(records):
        quarters = records[symbol]
        now = _value(quarters, target)
        ytd, ytd_ago = _year_so_far(quarters, target), _year_so_far(quarters, year_ago)
        forecast = _d(forecasts.get(symbol))
        plan = plans.get(symbol) or {}
        out.append({"symbol": symbol, "sector": sectors.get(symbol), "held": symbol in held, "reported": now is not None,
                    "npat": _s(now), "yoy": _r(_growth(now, _value(quarters, year_ago))), "qoq": _r(_growth(now, _value(quarters, _prev(target)))),
                    "ytd": _s(ytd), "ytd_ago": _s(ytd_ago), "ytd_yoy": _r(_growth(ytd, ytd_ago)), "plan_ratio": plan.get("ratio"), "plan_label": plan.get("label"),
                    "forecast": _s(forecast), "vs_forecast": _r(_growth(now, forecast)), "seasonal_share": _r(_seasonal_share(quarters, target)),
                    "review": reviews.get(symbol)})
    return out


def sector_table(rows: list[dict]) -> list[dict]:
    """Per sector: the year so far against a year before over the tickers that have both, the tickers up and down, the one adding most to
    the change and its share of it, and the growth without it."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        if r["sector"]:
            groups.setdefault(r["sector"], []).append(r)
    out = []
    for sector, members in groups.items():
        both = [r for r in members if r["ytd"] is not None and r["ytd_ago"] is not None]
        now, ago = sum((Decimal(r["ytd"]) for r in both), Decimal(0)), sum((Decimal(r["ytd_ago"]) for r in both), Decimal(0))
        top = max(both, key=lambda r: Decimal(r["ytd"]) - Decimal(r["ytd_ago"]), default=None)
        change = now - ago
        top_delta = Decimal(top["ytd"]) - Decimal(top["ytd_ago"]) if top else None
        without = _growth(now - Decimal(top["ytd"]), ago - Decimal(top["ytd_ago"])) if top and len(both) > 1 else None
        out.append({"sector": sector, "count": len(members), "reported": sum(1 for r in members if r["reported"]), "compared": len(both),
                    "ytd_now": _s(now) if both else None, "ytd_ago": _s(ago) if both else None, "ytd_growth": _r(_growth(now, ago)) if both else None,
                    "up": sum(1 for r in both if Decimal(r["ytd"]) > Decimal(r["ytd_ago"])), "down": sum(1 for r in both if Decimal(r["ytd"]) < Decimal(r["ytd_ago"])),
                    "top": top["symbol"] if top and top_delta > 0 else None,
                    "top_share": _r(top_delta / change) if top and top_delta > 0 and change > 0 else None,
                    "ytd_growth_without_top": _r(without) if top and top_delta > 0 else None})
    return sorted(out, key=lambda s: s["sector"])


def cash_rows(records: dict[str, dict], *, target: str) -> list[dict]:
    """The year so far: consolidated profit against cash from operations, for tickers with every quarter's cash flow. kind: "paper_profit"
    (a profit with cash going out), "cash_above" (cash at least twice the profit), or None. other_liabilities_change: liabilities other than
    borrowing since the end of last year, where payables, deposits taken, accruals and provisions sit (the store has no finer lines)."""
    y, _ = _split(target)
    out = []
    for symbol in sorted(records):
        quarters = records[symbol]
        npat, cfo = _year_so_far(quarters, target, "npat"), _year_so_far(quarters, target, "cfo")
        if npat is None or cfo is None:
            continue

        def other(q: str) -> Decimal | None:
            parts = [_value(quarters, q, f) for f in ("liabilities", "st_debt", "lt_debt")]
            return parts[0] - parts[1] - parts[2] if None not in parts else None
        now, start = other(target), other(f"{y - 1}-Q4")
        kind = "paper_profit" if npat > 0 and cfo < 0 else "cash_above" if npat > 0 and cfo >= CASH_ABOVE * npat else None
        out.append({"symbol": symbol, "npat": _s(npat), "cfo": _s(cfo), "ratio": _r(cfo / npat) if npat > 0 else None, "kind": kind,
                    "other_liabilities_change": _s(now - start) if now is not None and start is not None else None})
    return out
