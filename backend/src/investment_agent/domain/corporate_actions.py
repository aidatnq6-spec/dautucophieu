"""Dividends, bonus shares and splits as explicit ledger events.

An entitlement and its payment are two states of one action: income is
recognised once, at the entitlement, as a receivable, so the ex-date price drop
is not a fake loss; the payment only converts the receivable and records any
difference between expected and actual amounts as a traced adjustment.
Unsupported actions (rights issues, symbol changes, mergers) block the
affected security instead of being approximated.
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from .models import ContractModel, NonemptyId, SignedAmount, UnsignedAmount


class LedgerError(ValueError):
    def __init__(self, code: str, event_id: str | None = None):
        super().__init__(code if event_id is None else f"{code}: {event_id}")
        self.code, self.event_id = code, event_id


EventId = Annotated[str, Field(strict=True, pattern=r"^[A-Za-z0-9_-]{1,64}$")]
Quantity = Annotated[int, Field(strict=True, gt=0)]


class EventBase(ContractModel):
    event_id: EventId
    effective_at: date
    sequence: int = Field(strict=True, ge=0)
    settlement_date: date | None = None
    note: str = Field(default="", max_length=500)


class CashDividendEntitlement(EventBase):
    """Recorded at the ex-rights date with the owner's eligible quantity."""

    type: Literal["cash_dividend_entitlement"]
    action_id: EventId
    security_id: NonemptyId
    record_date: date
    payment_date: date | None
    eligible_quantity: Quantity
    expected_gross: UnsignedAmount
    expected_tax: UnsignedAmount


class CashDividendPayment(EventBase):
    type: Literal["cash_dividend_payment"]
    action_id: EventId
    received_net: UnsignedAmount
    tax_withheld: UnsignedAmount


class StockDividendEntitlement(EventBase):
    type: Literal["stock_dividend_entitlement"]
    action_id: EventId
    security_id: NonemptyId
    record_date: date
    eligible_quantity: Quantity
    shares_entitled: Quantity


class StockDividendCredit(EventBase):
    type: Literal["stock_dividend_credit"]
    action_id: EventId
    shares_credited: int = Field(strict=True, ge=0)
    cash_in_lieu: UnsignedAmount


class ShareSplit(EventBase):
    type: Literal["share_split"]
    action_id: EventId
    security_id: NonemptyId
    ratio_from: Quantity
    ratio_to: Quantity


class UnsupportedAction(EventBase):
    type: Literal["unsupported_action"]
    action_id: EventId
    security_id: NonemptyId
    kind: Literal["rights_issue", "symbol_change", "merger", "other"]


ACTION_EVENTS = (CashDividendEntitlement, CashDividendPayment, StockDividendEntitlement, StockDividendCredit, ShareSplit, UnsupportedAction)


class DividendAdjustment(ContractModel):
    action_id: EventId
    event_id: EventId
    amount: SignedAmount  # actual net − expected net


def apply_action(book, event):
    """Mutate a ledger book (see ledger._Book) for one corporate-action event."""
    kind = event.type
    if kind in {"cash_dividend_entitlement", "stock_dividend_entitlement", "share_split", "unsupported_action"}:
        if event.action_id in book.actions:
            raise LedgerError("duplicate_action", event.event_id)
        held = book.quantity.get(event.security_id, 0) + book.pending.get(event.security_id, 0)
        if kind in {"cash_dividend_entitlement", "stock_dividend_entitlement"} and event.eligible_quantity > held:
            raise LedgerError("eligible_exceeds_holding", event.event_id)
        book.actions[event.action_id] = event
    elif event.action_id not in book.actions:
        raise LedgerError("unknown_action", event.event_id)
    elif event.action_id in book.settled:
        raise LedgerError("action_already_settled", event.event_id)

    if kind == "cash_dividend_entitlement":
        expected = event.expected_gross - event.expected_tax
        if expected < 0:
            raise LedgerError("dividend_tax_exceeds_gross", event.event_id)
        book.receivable[event.action_id] = expected
        book.income += expected
    elif kind == "cash_dividend_payment":
        origin = book.actions[event.action_id]
        if origin.type != "cash_dividend_entitlement":
            raise LedgerError("action_type_mismatch", event.event_id)
        expected = book.receivable.pop(event.action_id)
        book.cash += event.received_net
        book.income += event.received_net - expected
        book.dividend_taxes += event.tax_withheld
        if event.received_net != expected:
            book.adjustments.append(DividendAdjustment(action_id=event.action_id, event_id=event.event_id,
                                                       amount=format(event.received_net - expected, "f")))
        book.settled.add(event.action_id)
    elif kind == "stock_dividend_entitlement":
        book.pending[event.security_id] = book.pending.get(event.security_id, 0) + event.shares_entitled
        book.pending_by_action[event.action_id] = event.shares_entitled
    elif kind == "stock_dividend_credit":
        origin = book.actions[event.action_id]
        if origin.type != "stock_dividend_entitlement":
            raise LedgerError("action_type_mismatch", event.event_id)
        security = origin.security_id
        book.pending[security] -= book.pending_by_action.pop(event.action_id)
        book.quantity[security] = book.quantity.get(security, 0) + event.shares_credited
        book.cash += event.cash_in_lieu
        book.income += event.cash_in_lieu
        book.settled.add(event.action_id)
        book.prune(security)
    elif kind == "share_split":
        security = event.security_id
        for counts in (book.quantity, book.pending):
            if counts.get(security):
                scaled, remainder = divmod(counts[security] * event.ratio_to, event.ratio_from)
                if remainder:
                    raise LedgerError("fractional_split", event.event_id)
                counts[security] = scaled
        book.settled.add(event.action_id)
    else:
        book.blocked.setdefault(event.security_id, []).append(event.kind)
