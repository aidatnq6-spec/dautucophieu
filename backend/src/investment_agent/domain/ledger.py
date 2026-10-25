"""Pure moving-average ledger replayed in (effective_at, sequence, event_id) order.

Buy fees and taxes enter cost; sell fees and taxes reduce proceeds. A sale
releases cost × sold / shares (one division, shares including pending bonus
shares), and selling every share releases the exact remaining cost, so cost
bought always equals cost remaining plus cost released.
"""

from collections import Counter
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import Field, TypeAdapter, model_validator

from .corporate_actions import (
    ACTION_EVENTS, CashDividendEntitlement, CashDividendPayment, DividendAdjustment, EventBase, LedgerError,
    Quantity, ShareSplit, StockDividendCredit, StockDividendEntitlement, UnsupportedAction, apply_action,
)
from .models import ContractModel, NonemptyId, SignedAmount, UnsignedAmount

__all__ = ["LedgerError", "LedgerEvent", "LedgerState", "parse_events", "replay", "order_key"]


class Trade(EventBase):
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


class CashMovement(EventBase):
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


class OpeningBalance(EventBase):
    """Starting point when earlier history is unavailable; prior realized gains stay unknown."""

    type: Literal["opening_balance"]
    cash: UnsignedAmount
    positions: tuple[OpeningPosition, ...]


LedgerEvent = Annotated[Union[Trade, CashMovement, OpeningBalance, CashDividendEntitlement, CashDividendPayment,
                              StockDividendEntitlement, StockDividendCredit, ShareSplit, UnsupportedAction],
                        Field(discriminator="type")]
_EVENTS = TypeAdapter(list[LedgerEvent])


class Holding(ContractModel):
    security_id: NonemptyId
    quantity: int = Field(strict=True, ge=0, description="Shares credited to the account")
    pending_quantity: int = Field(strict=True, ge=0, description="Entitled bonus/stock-dividend shares not yet credited")
    total_cost: UnsignedAmount
    average_cost: UnsignedAmount  # over quantity + pending_quantity
    blocked_by: tuple[str, ...] = ()


class LedgerState(ContractModel):
    started_on: date | None
    realized_before_start_unknown: bool
    event_count: int
    cash: UnsignedAmount
    positions: tuple[Holding, ...]
    realized_gain: SignedAmount
    dividend_income: SignedAmount
    dividend_receivable: UnsignedAmount
    dividend_adjustments: tuple[DividendAdjustment, ...]
    dividend_taxes_withheld: UnsignedAmount
    fees_paid: UnsignedAmount
    taxes_paid: UnsignedAmount
    deposits: UnsignedAmount
    withdrawals: UnsignedAmount
    net_contributions: SignedAmount


class _Book:
    def __init__(self):
        self.cash = self.realized = self.fees = self.taxes = self.deposits = self.withdrawals = Decimal(0)
        self.income = self.dividend_taxes = Decimal(0)
        self.quantity: dict[str, int] = {}
        self.pending: dict[str, int] = {}
        self.cost: dict[str, Decimal] = {}
        self.actions, self.receivable, self.pending_by_action = {}, {}, {}
        self.settled, self.adjustments, self.blocked = set(), [], {}

    def shares(self, security):
        return self.quantity.get(security, 0) + self.pending.get(security, 0)

    def prune(self, security):
        if not self.shares(security):
            for counts in (self.quantity, self.pending, self.cost):
                counts.pop(security, None)

    def trade(self, event):
        security = event.security_id
        if event.type == "buy":
            outlay = event.quantity * event.price + event.fee + event.tax
            self.cash -= outlay
            self.quantity[security] = self.quantity.get(security, 0) + event.quantity
            self.cost[security] = self.cost.get(security, Decimal(0)) + outlay
        else:
            if event.quantity > self.quantity.get(security, 0):
                raise LedgerError("oversell", event.event_id)
            shares = self.shares(security)
            released = self.cost[security] if event.quantity == shares else self.cost[security] * event.quantity / shares
            proceeds = event.quantity * event.price - event.fee - event.tax
            self.cash += proceeds
            self.realized += proceeds - released
            self.cost[security] -= released
            self.quantity[security] -= event.quantity
            self.prune(security)
        self.fees += event.fee
        self.taxes += event.tax


def parse_events(raw: list[dict]) -> list:
    return _EVENTS.validate_python(raw)


def order_key(event):
    return (event.effective_at, event.sequence, event.event_id)


def _s(value: Decimal) -> str:
    return format(value, "f")


def ordered_events(events: list) -> list:
    if any(n > 1 for n in Counter(e.event_id for e in events).values()):
        raise LedgerError("duplicate_event")
    if any(n > 1 for n in Counter((e.effective_at, e.sequence) for e in events).values()):
        raise LedgerError("ambiguous_order")
    ordered = sorted(events, key=order_key)
    openings = [e for e in ordered if e.type == "opening_balance"]
    if len(openings) > 1:
        raise LedgerError("multiple_opening_balances")
    if openings and ordered[0] is not openings[0]:
        raise LedgerError("before_opening_balance", ordered[0].event_id)
    return ordered


def replay(events: list) -> LedgerState:
    ordered = ordered_events(events)
    book = _Book()
    for event in ordered:
        if event.type == "opening_balance":
            book.cash = event.cash
            for p in event.positions:
                book.quantity[p.security_id] = book.quantity.get(p.security_id, 0) + p.quantity
                book.cost[p.security_id] = book.cost.get(p.security_id, Decimal(0)) + p.total_cost
        elif event.type == "deposit":
            book.cash += event.amount
            book.deposits += event.amount
        elif event.type == "withdrawal":
            book.cash -= event.amount
            book.withdrawals += event.amount
        elif event.type in {"buy", "sell"}:
            book.trade(event)
        elif isinstance(event, ACTION_EVENTS):
            apply_action(book, event)
        if book.cash < 0:
            raise LedgerError("cash_negative", event.event_id)

    holdings = tuple(Holding(security_id=s, quantity=book.quantity.get(s, 0), pending_quantity=book.pending.get(s, 0),
                             total_cost=_s(book.cost[s]), average_cost=_s(book.cost[s] / book.shares(s)),
                             blocked_by=tuple(book.blocked.get(s, ())))
                     for s in sorted(book.cost))
    return LedgerState(
        started_on=ordered[0].effective_at if ordered else None,
        realized_before_start_unknown=any(e.type == "opening_balance" for e in ordered), event_count=len(ordered),
        cash=_s(book.cash), positions=holdings, realized_gain=_s(book.realized), dividend_income=_s(book.income),
        dividend_receivable=_s(sum(book.receivable.values(), Decimal(0))), dividend_adjustments=tuple(book.adjustments),
        dividend_taxes_withheld=_s(book.dividend_taxes), fees_paid=_s(book.fees), taxes_paid=_s(book.taxes),
        deposits=_s(book.deposits), withdrawals=_s(book.withdrawals),
        net_contributions=_s(book.deposits - book.withdrawals),
    )
