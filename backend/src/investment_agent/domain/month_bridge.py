"""Vì sao tài sản tháng này thay đổi: the securities account's value at the last session before the month and at the month's last
session so far, and every đồng between them by cause:

- flows: deposits − withdrawals, and an opening balance (its shares at that day's close);
- ticker:<symbol>: shares × close at the end − shares × close at the start − what was paid for buys + what sells brought, before
  fees (an opening balance's shares enter at that day's close);
- dividends: cash dividends received and cash paid in lieu of fractional shares;
- costs: trading fees and taxes (negative);
- other: whatever is left (zero unless the ledger holds a cash effect not listed above): shown, never spread over the rest.

The value is cash plus shares (credited and pending) at the session's close, as on Hiệu quả danh mục. A ticker held at either end
without a close that day stops the bridge, named. Closes are in thousand đồng.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .ledger import ordered_events, replay


def _s(value: Decimal) -> str:
    q = value.quantize(Decimal(1), ROUND_HALF_UP)
    return format(q, "f") if q != 0 else "0"


def _close(closes: dict, symbol: str, day: date) -> Decimal | None:
    v = (closes.get(symbol) or {}).get(day)
    return Decimal(str(v)) * 1000 if v is not None else None


def _holdings(events: list, day: date | None) -> tuple[Decimal, dict[str, int]]:
    if day is None:
        return Decimal(0), {}
    state = replay([e for e in events if e.effective_at <= day])
    return Decimal(state.cash), {h.security_id: h.quantity + h.pending_quantity for h in state.positions if h.quantity + h.pending_quantity}


def month_bridge(events: list, *, closes: dict[str, dict[date, float]], sessions: list[date], month: str) -> dict:
    """sessions: the days with an index close (VN-Index), the trading days the value is taken on."""
    days = sorted(sessions)
    in_month = [d for d in days if d.isoformat()[:7] == month]
    if not in_month or not events:
        return {"status": "no_sessions", "month": month}
    end = in_month[-1]
    first_event = min(e.effective_at for e in events)
    before = [d for d in days if d.isoformat()[:7] < month and d >= first_event]
    return {**bridge_between(events, closes=closes, start=before[-1] if before else None, end=end), "month": month}


def bridge_between(events: list, *, closes: dict[str, dict[date, float]], start: date | None, end: date) -> dict:
    """The same split between two closes: start (None = before the first event, from nothing) and end."""
    cash_s, held_s = _holdings(events, start)
    cash_e, held_e = _holdings(events, end)
    missing = sorted({s for s in held_s if _close(closes, s, start) is None} | {s for s in held_e if _close(closes, s, end) is None})
    window = [e for e in ordered_events(events) if (start is None or e.effective_at > start) and e.effective_at <= end]
    openings = [(e, p) for e in window if e.type == "opening_balance" for p in e.positions]
    missing = sorted(set(missing) | {p.security_id for e, p in openings if _close(closes, p.security_id, e.effective_at) is None})
    if missing:
        return {"status": "missing_prices", "missing": missing, "start_day": start.isoformat() if start else None,
                "end_day": end.isoformat()}
    value = lambda cash, held, day: cash + sum((q * _close(closes, s, day) for s, q in held.items()), Decimal(0))  # noqa: E731
    v_start, v_end = value(cash_s, held_s, start) if start else Decimal(0), value(cash_e, held_e, end)
    flows, dividends, costs = Decimal(0), Decimal(0), Decimal(0)
    tickers: dict[str, Decimal] = {s: q * _close(closes, s, end) for s, q in held_e.items()}
    for s, q in held_s.items():
        tickers[s] = tickers.get(s, Decimal(0)) - q * _close(closes, s, start)
    for e in window:
        if e.type == "deposit":
            flows += e.amount
        elif e.type == "withdrawal":
            flows -= e.amount
        elif e.type == "opening_balance":
            flows += e.cash
            for p in e.positions:
                worth = p.quantity * _close(closes, p.security_id, e.effective_at)
                flows += worth
                tickers[p.security_id] = tickers.get(p.security_id, Decimal(0)) - worth
        elif e.type in ("buy", "sell"):
            gross = e.quantity * e.price
            tickers[e.security_id] = tickers.get(e.security_id, Decimal(0)) + (gross if e.type == "sell" else -gross)
            costs -= e.fee + e.tax
        elif e.type == "cash_dividend_payment":
            dividends += e.received_net
        elif e.type == "stock_dividend_credit":
            dividends += e.cash_in_lieu
    steps = [{"id": "flows", "amount": flows}]
    steps += [{"id": f"ticker:{s}", "symbol": s, "amount": a} for s, a in sorted(tickers.items(), key=lambda kv: -abs(kv[1]))]
    steps += [{"id": "dividends", "amount": dividends}, {"id": "costs", "amount": costs}]
    other = v_end - v_start - sum((s["amount"] for s in steps), Decimal(0))
    return {"status": "ok", "start_day": start.isoformat() if start else None, "end_day": end.isoformat(),
            "start": _s(v_start), "end": _s(v_end), "other": _s(other),
            "steps": [{**s, "amount": _s(s["amount"])} for s in steps if _s(s["amount"]) != "0"]}


CALENDAR_WEEKS = 26


def daily_moves(events: list, *, closes: dict[str, dict[date, float]], sessions: list[date], today: date, weeks: int = CALENDAR_WEEKS) -> list[dict]:
    """Each session of the last `weeks` weeks since the ledger began: the account's gain that day (the change in value less money in
    or out), as a share of the value at the close before, and the three tickers that moved it most. A day a held ticker has no close
    is listed as missing, not guessed."""
    from datetime import timedelta
    if not events:
        return []
    first = min(e.effective_at for e in events)
    days = sorted(d for d in sessions if first <= d <= today)
    out = []
    for prev, day in zip(days, days[1:]):
        if day < today - timedelta(weeks=weeks):
            continue
        b = bridge_between(events, closes=closes, start=prev, end=day)
        if b["status"] != "ok":
            out.append({"date": day.isoformat(), "status": "missing", "missing": b["missing"]})
            continue
        flows = sum((Decimal(s["amount"]) for s in b["steps"] if s["id"] == "flows"), Decimal(0))
        gain = Decimal(b["end"]) - Decimal(b["start"]) - flows
        base = Decimal(b["start"])
        tickers = sorted((s for s in b["steps"] if s.get("symbol")), key=lambda s: -abs(Decimal(s["amount"])))[:3]
        out.append({"date": day.isoformat(), "status": "ok", "gain": _s(gain),
                    "return": format((gain / base).quantize(Decimal("0.0001"), ROUND_HALF_UP).normalize(), "f") if base > 0 else None,
                    "tickers": [{"symbol": s["symbol"], "amount": s["amount"]} for s in tickers]})
    return out
