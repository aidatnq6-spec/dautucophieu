"""Accounting cash versus buying power, and credited versus tradable shares.

No T+ or lot rule is assumed (see docs/decisions/market-rules.md). Buying power
comes from owner confirmation for the same day, otherwise from settlement dates
recorded on the ledger events; a sale without a settlement date makes buying
power unknown rather than optimistic. Owner figures are capped by the ledger.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from .ledger import ordered_events, replay
from .models import ContractModel, UnsignedAmount


class OwnerAvailability(ContractModel):
    as_of: date
    buying_power: UnsignedAmount
    tradable: dict[str, int]


class Availability(ContractModel):
    as_of: date
    accounting_cash: UnsignedAmount
    pending_sale_proceeds: UnsignedAmount | None
    buying_power: UnsignedAmount | None
    buying_power_basis: Literal["owner_confirmed", "ledger_settlement_dates", "unknown"]
    tradable: dict[str, int]
    tradable_basis: Literal["owner_confirmed", "ledger_settlement_dates", "unknown"]
    warnings: tuple[Literal["confirmed_cash_exceeds_ledger", "confirmed_quantity_exceeds_ledger"], ...]


def availability(events: list, *, as_of: date, confirmed: OwnerAvailability | None = None) -> Availability:
    past = [e for e in ordered_events(events) if e.effective_at <= as_of]
    state = replay(past)
    pending_cash, cash_unknown, unsettled, qty_unknown = Decimal(0), False, {}, False
    for e in past:
        if e.type not in {"buy", "sell"}:
            continue
        if e.settlement_date is None:
            cash_unknown |= e.type == "sell"
            qty_unknown |= e.type == "buy"
        elif e.settlement_date > as_of:
            if e.type == "sell":
                pending_cash += e.quantity * e.price - e.fee - e.tax
            else:
                unsettled[e.security_id] = unsettled.get(e.security_id, 0) + e.quantity
    credited = {h.security_id: h.quantity for h in state.positions}
    estimate = {s: max(q - unsettled.get(s, 0), 0) for s, q in credited.items()}

    warnings = []
    if confirmed is not None and confirmed.as_of == as_of:
        power, power_basis = confirmed.buying_power, "owner_confirmed"
        if power > state.cash:
            power = state.cash
            warnings.append("confirmed_cash_exceeds_ledger")
        tradable = {s: min(confirmed.tradable.get(s, 0), q) for s, q in credited.items()}
        if any(confirmed.tradable.get(s, 0) > q for s, q in credited.items()) or set(confirmed.tradable) - set(credited):
            warnings.append("confirmed_quantity_exceeds_ledger")
        tradable_basis = "owner_confirmed"
    else:
        power = None if cash_unknown else state.cash - pending_cash
        power_basis = "unknown" if cash_unknown else "ledger_settlement_dates"
        tradable, tradable_basis = estimate, "unknown" if qty_unknown else "ledger_settlement_dates"
    return Availability(
        as_of=as_of, accounting_cash=format(state.cash, "f"),
        pending_sale_proceeds=None if cash_unknown else format(pending_cash, "f"),
        buying_power=None if power is None else format(power, "f"), buying_power_basis=power_basis,
        tradable=tradable, tradable_basis=tradable_basis, warnings=tuple(warnings),
    )
