"""Absolute investment gain since tracking began, reconciled against assets.

end assets − start assets − net contributions
    = realized + unrealized + dividend income − unrealized already present at start

Deposits and withdrawals are contributions, never gains. Time-weighted and
money-weighted returns are not calculated until cash-flow timing is verified.
"""

from decimal import Decimal
from typing import Literal

from .ledger import replay
from .models import ContractModel, NonemptyId, SignedAmount, UnsignedAmount
from .positions import value_positions


class Performance(ContractModel):
    status: Literal["complete", "incomplete", "blocked"]
    started_on: str | None
    missing_prices: tuple[NonemptyId, ...]
    blocked_securities: tuple[NonemptyId, ...]
    start_assets: UnsignedAmount | None
    end_assets: UnsignedAmount | None
    net_contributions: SignedAmount
    realized_gain: SignedAmount
    unrealized_gain: SignedAmount | None
    unrealized_before_start: SignedAmount | None
    dividend_income: SignedAmount
    total_gain: SignedAmount | None
    reconciliation_difference: SignedAmount | None
    realized_before_start_unknown: bool
    return_measures: Literal["not_calculated"] = "not_calculated"


def _s(value):
    return None if value is None else format(value, "f")


def performance(events: list, *, end_prices: dict[str, Decimal | None], start_prices: dict[str, Decimal | None] | None = None) -> Performance:
    state = replay(events)
    start_prices = start_prices or {}
    opening = next((e for e in events if e.type == "opening_balance"), None)
    missing = []

    start = Decimal(0)
    before_start = Decimal(0)
    if opening is not None:
        start = opening.cash
        for p in opening.positions:
            price = start_prices.get(p.security_id)
            if price is None:
                missing.append(p.security_id)
                continue
            start += p.quantity * price
            before_start += p.quantity * price - p.total_cost

    rows = value_positions(state, end_prices)
    missing.extend(r.security_id for r in rows if r.market_value is None)
    blocked = tuple(h.security_id for h in state.positions if h.blocked_by)
    status = "blocked" if blocked else "incomplete" if missing else "complete"

    end = unrealized = total = difference = None
    if status == "complete":
        end = state.cash + state.dividend_receivable + sum((r.market_value for r in rows), Decimal(0))
        unrealized = sum((r.unrealized_gain for r in rows), Decimal(0))
        total = state.realized_gain + unrealized + state.dividend_income - before_start
        difference = (end - start - state.net_contributions) - total
    return Performance(
        status=status, started_on=_s(state.started_on), missing_prices=tuple(sorted(set(missing))), blocked_securities=blocked,
        start_assets=_s(start) if status == "complete" else None, end_assets=_s(end), net_contributions=_s(state.net_contributions),
        realized_gain=_s(state.realized_gain), unrealized_gain=_s(unrealized),
        unrealized_before_start=_s(before_start) if status == "complete" else None, dividend_income=_s(state.dividend_income),
        total_gain=_s(total), reconciliation_difference=_s(difference),
        realized_before_start_unknown=state.realized_before_start_unknown,
    )
