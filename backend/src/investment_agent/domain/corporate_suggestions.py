"""Cổ tức và quyền vào sổ: ledger lines drafted from the Lịch sự kiện for the owner to check against the broker's papers and save,
and the taxes and fees the ledger records each year.

Nothing is written here: a draft is a suggestion the owner edits and saves. Shares entitled are those credited in the ledger from
trades before the ex-rights date. A source without an amount or ratio gets no draft; rights issues are only pointed out, since the
ledger does not support them (docs/decisions/market-rules.md)."""

import math
import re
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from investment_agent.domain.corporate_actions import (CashDividendEntitlement, CashDividendPayment, StockDividendCredit,
                                                       StockDividendEntitlement)
from investment_agent.domain.ledger import Trade, ordered_events, replay

DIVIDEND_TAX = Decimal("0.05")  # config/market-rules-hose.json dividend_tax_rate
LOOKBACK_DAYS, AHEAD_DAYS = 400, 30
_STOCK = re.compile(r"cổ tức bằng cổ phiếu|cổ phiếu thưởng", re.IGNORECASE)
_RIGHTS = re.compile(r"quyền mua", re.IGNORECASE)
_ID = re.compile(r"[^A-Za-z0-9_-]")


def classify(event: dict) -> str | None:
    """cash (with an amount per share), stock (bonus shares or a stock dividend, with a ratio), rights, or None."""
    if event.get("kind") == "dividend_cash":
        return "cash" if event.get("value_per_share") else None
    if event.get("kind") != "issue":
        return None
    title = event.get("title") or ""
    if _RIGHTS.search(title):
        return "rights"
    return "stock" if _STOCK.search(title) and event.get("ratio") else None


def _s(value: Decimal) -> str:
    return format(value.quantize(Decimal(1), ROUND_HALF_UP), "f")


def _eligible(events: list, symbol: str, exright: date) -> int:
    before = [e for e in events if e.effective_at < exright]
    if not before:
        return 0
    return next((p.quantity for p in replay(before).positions if p.security_id == symbol), 0)


def suggestions(events, corporate: list[dict], *, today: date, dismissed: set[str]) -> list[dict]:
    events = ordered_events(list(events))
    entitlements = [e for e in events if isinstance(e, (CashDividendEntitlement, StockDividendEntitlement))]
    paid = {e.action_id for e in events if isinstance(e, CashDividendPayment)}
    credited = {e.action_id for e in events if isinstance(e, StockDividendCredit)}
    out = []
    for ev in sorted(corporate, key=lambda e: (e.get("exright") or "", e["symbol"])):
        kind = classify(ev)
        if kind is None or not ev.get("exright") or ev["id"] in dismissed:
            continue
        exright = date.fromisoformat(ev["exright"])
        if not today - timedelta(days=LOOKBACK_DAYS) <= exright <= today + timedelta(days=AHEAD_DAYS):
            continue
        symbol, action = ev["symbol"], _ID.sub("-", ev["id"])[:64]
        base = {"id": ev["id"], "symbol": symbol, "kind": kind, "title": ev.get("title") or "", "exright": ev["exright"], "record": ev.get("record"),
                "payout": ev.get("payout"), "value_per_share": ev.get("value_per_share"), "ratio": ev.get("ratio")}
        if exright > today:
            held = next((p.quantity for p in replay(events).positions if p.security_id == symbol), 0) if events else 0
            if held:
                out.append({**base, "status": "upcoming", "eligible": held, "draft": None})
            continue
        eligible = _eligible(events, symbol, exright)
        if not eligible:
            continue
        if kind == "rights":
            out.append({**base, "status": "rights", "eligible": eligible, "draft": None})
            continue
        recorded = next((e for e in entitlements if e.action_id == action or (e.security_id == symbol and ev.get("record")
                                                                              and e.record_date.isoformat() == ev["record"])), None)
        if recorded is None:
            if kind == "cash":
                gross = Decimal(str(ev["value_per_share"])) * eligible
                draft = {"type": "cash_dividend_entitlement", "effective_at": ev["exright"], "action_id": action, "security_id": symbol,
                         "record_date": ev.get("record") or ev["exright"], "payment_date": ev.get("payout"), "eligible_quantity": eligible,
                         "expected_gross": _s(gross), "expected_tax": _s(gross * DIVIDEND_TAX)}
            else:
                draft = {"type": "stock_dividend_entitlement", "effective_at": ev["exright"], "action_id": action, "security_id": symbol,
                         "record_date": ev.get("record") or ev["exright"], "eligible_quantity": eligible,
                         "shares_entitled": math.floor(Decimal(str(ev["ratio"])) * eligible)}
            out.append({**base, "status": "to_record", "eligible": eligible, "draft": draft})
        elif isinstance(recorded, CashDividendEntitlement) and recorded.action_id not in paid:
            due = recorded.payment_date or (date.fromisoformat(ev["payout"]) if ev.get("payout") else None)
            if due is None or due > today:
                out.append({**base, "status": "waiting", "eligible": recorded.eligible_quantity, "draft": None})
            else:
                out.append({**base, "status": "to_receive", "eligible": recorded.eligible_quantity, "draft": {
                    "type": "cash_dividend_payment", "effective_at": due.isoformat(), "action_id": recorded.action_id,
                    "received_net": _s(recorded.expected_gross - recorded.expected_tax), "tax_withheld": _s(recorded.expected_tax)}})
        elif isinstance(recorded, StockDividendEntitlement) and recorded.action_id not in credited:
            out.append({**base, "status": "to_credit", "eligible": recorded.eligible_quantity, "draft": {
                "type": "stock_dividend_credit", "effective_at": today.isoformat(), "action_id": recorded.action_id,
                "shares_credited": recorded.shares_entitled, "cash_in_lieu": "0"}})
    return out


def yearly_costs(events) -> list[dict]:
    """Per calendar year, as recorded: sale value, trading fees, sale tax, cash dividends received (net plus tax withheld) and the
    dividend tax withheld."""
    years: dict[int, dict[str, Decimal]] = {}
    for e in ordered_events(list(events)):
        y = years.setdefault(e.effective_at.year, {k: Decimal(0) for k in ("sell_value", "fees", "sell_tax", "dividends", "dividend_tax")})
        if isinstance(e, Trade):
            y["fees"] += e.fee
            if e.type == "sell":
                y["sell_value"] += e.price * e.quantity
                y["sell_tax"] += e.tax
        elif isinstance(e, CashDividendPayment):
            y["dividends"] += e.received_net + e.tax_withheld
            y["dividend_tax"] += e.tax_withheld
    return [{"year": year, **{k: _s(v) for k, v in y.items()}, "total": _s(y["fees"] + y["sell_tax"] + y["dividend_tax"])}
            for year, y in sorted(years.items()) if any(y.values())]
