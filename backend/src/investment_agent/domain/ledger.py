"""Pure moving-average ledger replayed in (effective_at, sequence, event_id) order.

Buy fees and taxes enter cost; sell fees and taxes reduce proceeds. A sale
releases quantity × average cost (computed as cost × sold / held so the
division happens once), and a full sale releases the exact remaining cost, so
cost bought always equals cost remaining plus cost released.
"""

from collections import Counter
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import Field, TypeAdapter, model_validator

from .models import ContractModel, NonemptyId, SignedAmount, UnsignedAmount

EventId = Annotated[str, Field(strict=True, pattern=r"^[A-Za-z0-9_-]{1,64}$")]
Quantity = Annotated[int, Field(strict=True, gt=0)]


class LedgerError(ValueError):
    def __init__(self, code: str, event_id: str | None = None):
        super().__init__(code if event_id is None else f"{code}: {event_id}")
        self.code, self.event_id = code, event_id


class _Event(ContractModel):
    event_id: EventId
    effective_at: date
    sequence: int = Field(strict=True, ge=0)
    settlement_date: date | None = None
    note: str = Field(default="", max_length=500)


class Trade(_Event):
    type: Literal["buy", "sell"]
    security_id: NonemptyId
    quantity: Quantity
    price: UnsignedAmount
    fee: UnsignedAmount
    tax: UnsignedAmount

    @model_validator(mode="after")
    def _priced(self):
        if self.price <= 0:
            raise ValueError("price must be positive")
        return self


class CashMovement(_Event):
    type: Literal["deposit", "withdrawal"]
    amount: UnsignedAmount

    @model_validator(mode="after")
    def _positive(self):
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        return self


class OpeningPosition(ContractModel):
    security_id: NonemptyId
    quantity: Quantity
    total_cost: UnsignedAmount


class OpeningBalance(_Event):
    """Starting point when earlier history is unavailable; prior realized gains stay unknown."""

    type: Literal["opening_balance"]
    cash: UnsignedAmount
    positions: tuple[OpeningPosition, ...]


LedgerEvent = Annotated[Union[Trade, CashMovement, OpeningBalance], Field(discriminator="type")]
_EVENTS = TypeAdapter(list[LedgerEvent])


class Holding(ContractModel):
    security_id: NonemptyId
    quantity: Quantity
    total_cost: UnsignedAmount
    average_cost: UnsignedAmount


class LedgerState(ContractModel):
    started_on: date | None
    realized_before_start_unknown: bool
    event_count: int
    cash: UnsignedAmount
    positions: tuple[Holding, ...]
    realized_gain: SignedAmount
    fees_paid: UnsignedAmount
    taxes_paid: UnsignedAmount
    deposits: UnsignedAmount
    withdrawals: UnsignedAmount
    net_contributions: SignedAmount


def parse_events(raw: list[dict]) -> list:
    return _EVENTS.validate_python(raw)


def order_key(event):
    return (event.effective_at, event.sequence, event.event_id)


def _s(value: Decimal) -> str:
    return format(value, "f")


def replay(events: list) -> LedgerState:
    if any(n > 1 for n in Counter(e.event_id for e in events).values()):
        raise LedgerError("duplicate_event")
    slots = Counter((e.effective_at, e.sequence) for e in events)
    if any(n > 1 for n in slots.values()):
        raise LedgerError("ambiguous_order")
    ordered = sorted(events, key=order_key)
    openings = [e for e in ordered if e.type == "opening_balance"]
    if len(openings) > 1:
        raise LedgerError("multiple_opening_balances")
    if openings and ordered[0] is not openings[0]:
        raise LedgerError("before_opening_balance", ordered[0].event_id)

    cash = realized = fees = taxes = deposits = withdrawals = Decimal(0)
    quantity: dict[str, int] = {}
    cost: dict[str, Decimal] = {}
    for event in ordered:
        if event.type == "opening_balance":
            cash = event.cash
            for p in event.positions:
                quantity[p.security_id] = quantity.get(p.security_id, 0) + p.quantity
                cost[p.security_id] = cost.get(p.security_id, Decimal(0)) + p.total_cost
        elif event.type == "deposit":
            cash += event.amount
            deposits += event.amount
        elif event.type == "withdrawal":
            cash -= event.amount
            withdrawals += event.amount
        elif event.type == "buy":
            outlay = event.quantity * event.price + event.fee + event.tax
            cash -= outlay
            quantity[event.security_id] = quantity.get(event.security_id, 0) + event.quantity
            cost[event.security_id] = cost.get(event.security_id, Decimal(0)) + outlay
            fees += event.fee
            taxes += event.tax
        else:
            held = quantity.get(event.security_id, 0)
            if event.quantity > held:
                raise LedgerError("oversell", event.event_id)
            released = cost[event.security_id] if event.quantity == held else cost[event.security_id] * event.quantity / held
            proceeds = event.quantity * event.price - event.fee - event.tax
            cash += proceeds
            realized += proceeds - released
            cost[event.security_id] -= released
            quantity[event.security_id] = held - event.quantity
            if not quantity[event.security_id]:
                del quantity[event.security_id], cost[event.security_id]
            fees += event.fee
            taxes += event.tax
        if cash < 0:
            raise LedgerError("cash_negative", event.event_id)

    holdings = tuple(Holding(security_id=s, quantity=q, total_cost=_s(cost[s]), average_cost=_s(cost[s] / q))
                     for s, q in sorted(quantity.items()))
    return LedgerState(
        started_on=ordered[0].effective_at if ordered else None, realized_before_start_unknown=bool(openings),
        event_count=len(ordered), cash=_s(cash), positions=holdings, realized_gain=_s(realized), fees_paid=_s(fees),
        taxes_paid=_s(taxes), deposits=_s(deposits), withdrawals=_s(withdrawals), net_contributions=_s(deposits - withdrawals),
    )
