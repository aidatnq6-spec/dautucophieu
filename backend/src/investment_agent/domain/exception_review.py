"""Strong-growth exception review: every condition is checked, none is implied by a score."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from pydantic import AwareDatetime

from .investable_capital import CapitalAssessment
from .models import ContractModel, Ratio, UnsignedAmount
from .risk import RiskAssessment


class ExceptionReview(ContractModel):
    holding_extension_confirmed: bool
    holding_extension_reason: str
    funds_not_borrowed: bool
    reserve_confirmed: bool
    cashflow_reviewed_at: date
    untouched_at_least_one_year: bool
    acknowledged_scenarios: tuple[Ratio, ...]
    confirmed_at: AwareDatetime


class LossScenario(ContractModel):
    drop: Ratio
    equity_loss: UnsignedAmount
    capital_after: UnsignedAmount
    share_of_capital: Ratio


def _s(value: Decimal) -> str:
    return format(value, "f")


def loss_scenarios(policy, capital: CapitalAssessment, equity_ratio: Decimal) -> tuple[LossScenario, ...]:
    """Illustrations of the equity sleeve falling; not maximum-loss estimates."""
    base = capital.investable_capital or Decimal(0)
    rows = []
    for drop in policy.exception.loss_scenarios:
        loss = base * equity_ratio * drop
        rows.append(LossScenario(drop=_s(drop), equity_loss=_s(loss), capital_after=_s(base - loss), share_of_capital=_s(equity_ratio * drop)))
    return tuple(rows)


def review_exception(policy, review: ExceptionReview | None, *, risk: RiskAssessment, capital: CapitalAssessment, now: datetime) -> tuple[str, ...]:
    """Missing condition codes; empty means the review itself is complete."""
    if review is None:
        return ("review_missing",)
    valid_for = timedelta(days=policy.exception.review_valid_days)
    missing = []
    if risk.group not in policy.exception.eligible_groups:
        missing.append("group_not_eligible")
    if risk.blocks_capital_increase or not risk.ready_for_allocation:
        missing.append("risk_capacity")
    if capital.status != "ready":
        missing.append("capital_not_ready")
    if not review.holding_extension_confirmed or not review.holding_extension_reason.strip():
        missing.append("holding_extension")
    if not review.funds_not_borrowed:
        missing.append("borrowed_funds")
    if not review.reserve_confirmed or any(w.code.startswith("emergency_reserve") for w in capital.warnings):
        missing.append("reserve")
    if not review.untouched_at_least_one_year:
        missing.append("untouched_one_year")
    if sorted(review.acknowledged_scenarios) != sorted(policy.exception.loss_scenarios):
        missing.append("loss_scenarios")
    age = now - review.confirmed_at
    if age < timedelta(0) or age > valid_for:
        missing.append("review_expired")
    if not timedelta(0) <= now.date() - review.cashflow_reviewed_at <= valid_for:
        missing.append("cashflow_outdated")
    return tuple(missing)
