"""Mark ledger holdings to market; a missing price is reported, never valued at zero."""

from decimal import Decimal
from typing import Literal

from .ledger import LedgerState
from .models import ContractModel, NonemptyId, SignedAmount, UnsignedAmount


class PositionValue(ContractModel):
    security_id: NonemptyId
    quantity: int
    total_cost: UnsignedAmount
    price: UnsignedAmount | None
    market_value: UnsignedAmount | None
    unrealized_gain: SignedAmount | None
    quality_status: Literal["verified", "missing"]


def value_positions(state: LedgerState, prices: dict[str, Decimal | None]) -> tuple[PositionValue, ...]:
    rows = []
    for h in state.positions:
        price = prices.get(h.security_id)
        if price is None:
            rows.append(PositionValue(security_id=h.security_id, quantity=h.quantity, total_cost=format(h.total_cost, "f"),
                                      price=None, market_value=None, unrealized_gain=None, quality_status="missing"))
            continue
        value = h.quantity * price
        rows.append(PositionValue(security_id=h.security_id, quantity=h.quantity, total_cost=format(h.total_cost, "f"),
                                  price=format(price, "f"), market_value=format(value, "f"),
                                  unrealized_gain=format(value - h.total_cost, "f"), quality_status="verified"))
    return tuple(rows)
