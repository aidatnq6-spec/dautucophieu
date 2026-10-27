"""Portfolio performance since the first ledger event: time-weighted (deposits and withdrawals do not count as gains),
rebased to 100 and compared with VN-Index over the same sessions. A session without a close for a held ticker is skipped
rather than valued with a guess."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .ledger import replay

_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")


def _external(events: list, start_excl: date | None, end_incl: date, closes: dict, day: date) -> Decimal:
    """Money that entered (+) or left (−) the account in (start_excl, end_incl]: deposits, withdrawals and opening balances."""
    flow = Decimal(0)
    for e in events:
        if (start_excl is None or e.effective_at > start_excl) and e.effective_at <= end_incl:
            if e.type == "deposit":
                flow += e.amount
            elif e.type == "withdrawal":
                flow -= e.amount
            elif e.type == "opening_balance":
                flow += e.cash + sum((Decimal(p.quantity) * Decimal(str(closes[p.security_id][day])) for p in e.positions), Decimal(0))
    return flow


def performance(events: list, *, closes: dict[str, dict[date, float]], index: dict[date, float], today: date) -> dict:
    if not events:
        return {"series": [], "monthly": [], "total": None, "skipped_days": []}
    start = min(e.effective_at for e in events)
    series, skipped = [], []
    prev_day, prev_value, level, base_index = None, None, Decimal(100), None
    for day in sorted(d for d in index if start <= d <= today):
        state = replay([e for e in events if e.effective_at <= day])
        try:
            value = Decimal(state.cash) + sum((Decimal(h.quantity + h.pending_quantity) * Decimal(str(closes[h.security_id][day]))
                                               for h in state.positions), Decimal(0))
            flow = _external(events, prev_day, day, closes, day)
        except KeyError:
            skipped.append(day.isoformat())
            continue
        if prev_value is None:
            base_index = Decimal(str(index[day]))
        elif prev_value > 0:
            level *= (value - flow) / prev_value
        prev_day, prev_value = day, value
        series.append({"date": day.isoformat(), "portfolio": str(level.quantize(_Q2, ROUND_HALF_UP)),
                       "vnindex": str((Decimal(str(index[day])) / base_index * 100).quantize(_Q2, ROUND_HALF_UP)),
                       "value": str(value.quantize(Decimal(1), ROUND_HALF_UP)), "_level": level,
                       "_index": Decimal(str(index[day])) / base_index * 100})
    monthly, last = [], {"portfolio": Decimal(100), "vnindex": Decimal(100)}
    for i, point in enumerate(series):
        is_month_end = i == len(series) - 1 or series[i + 1]["date"][:7] != point["date"][:7]
        if is_month_end:
            monthly.append({"month": point["date"][:7],
                            "portfolio": str((point["_level"] / last["portfolio"] - 1).quantize(_Q4, ROUND_HALF_UP)),
                            "vnindex": str((point["_index"] / last["vnindex"] - 1).quantize(_Q4, ROUND_HALF_UP))})
            last = {"portfolio": point["_level"], "vnindex": point["_index"]}
    total = None
    if series:
        end = series[-1]
        total = {"portfolio": str((end["_level"] / 100 - 1).quantize(_Q4, ROUND_HALF_UP)),
                 "vnindex": str((end["_index"] / 100 - 1).quantize(_Q4, ROUND_HALF_UP)), "since": series[0]["date"], "days": len(series)}
    for point in series:
        point.pop("_level"), point.pop("_index")
    return {"series": series, "monthly": monthly, "total": total, "skipped_days": skipped}


def benchmarks(total: dict | None, *, end: str | None, deposit_rate: str | None, cpi: tuple[str, str] | None) -> dict:
    """Saving at the 12-month deposit rate and inflation at the latest CPI (year on year), both scaled to the same period as the
    portfolio's return; real return = portfolio after inflation. Missing inputs stay None, never guessed."""
    if not total or not end:
        return {"days": None, "deposit": None, "deposit_rate": deposit_rate, "inflation": None, "cpi_yoy": cpi[1] if cpi else None,
                "cpi_month": cpi[0] if cpi else None, "real": None}
    days = (date.fromisoformat(end) - date.fromisoformat(total["since"])).days
    scale = lambda annual: Decimal(str((1 + float(Decimal(annual) / 100)) ** (days / 365) - 1))  # noqa: E731
    deposit = scale(deposit_rate) if deposit_rate is not None else None
    inflation = scale(cpi[1]) if cpi else None
    real = (1 + Decimal(total["portfolio"])) / (1 + inflation) - 1 if inflation is not None else None
    q = lambda d: str(d.quantize(_Q4, ROUND_HALF_UP)) if d is not None else None  # noqa: E731
    return {"days": days, "deposit": q(deposit), "deposit_rate": deposit_rate, "inflation": q(inflation), "cpi_yoy": cpi[1] if cpi else None,
            "cpi_month": cpi[0] if cpi else None, "real": q(real)}
