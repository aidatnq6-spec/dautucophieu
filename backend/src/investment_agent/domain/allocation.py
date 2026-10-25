"""Equity targets on confirmed investable capital, checked on the post-trade portfolio.

Limits govern new buys only. A holding that drifts above target because prices
rose produces a warning; this module never emits sell orders.
"""

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field

from .exception_review import ExceptionReview, review_exception
from .investable_capital import CapitalAssessment
from .models import ContractModel, NonemptyId, Ratio, UnsignedAmount
from .pinned import CONFIG_DIR, load_pinned
from .profile import ProfileFreshness
from .risk import RiskAssessment

POLICY_PATH = CONFIG_DIR / "allocation-policy.json"
PINNED_DIGESTS = {
    "allocation-2026-10-25.1": "8549e5d5dc28528aa28a4f7c5d5aaf9ff1b8ac3b94bcd8feddec969a0e3eece3",
}


class ExceptionPolicy(ContractModel):
    eligible_groups: tuple[str, ...]
    max_equity: Ratio
    min_issuers: int = Field(strict=True, ge=1)
    min_industries: int = Field(strict=True, ge=1)
    max_issuer: Ratio
    max_industry: Ratio
    loss_scenarios: tuple[Ratio, ...]
    review_valid_days: int = Field(strict=True, ge=1)


class AllocationPolicy(ContractModel):
    version: str
    digest: str = ""
    status: Literal["initial_unvalidated"]
    notice: str
    baseline_equity: dict[str, Ratio]
    exception: ExceptionPolicy


class Position(ContractModel):
    issuer_id: NonemptyId
    control_group_id: NonemptyId | None  # issuer_id itself when confirmed independent; None = unknown
    industry: NonemptyId | None
    market_value: UnsignedAmount


class AllocationWarning(ContractModel):
    code: Literal["above_target_from_price"]
    amount: UnsignedAmount


class AllocationDecision(ContractModel):
    status: Literal["ok", "blocked"]
    policy_version: str
    risk_group: str
    target_ratio: Ratio | None
    current_ratio: UnsignedAmount | None = Field(description="Equity / investable capital; can exceed 1 when deductions exceed cash")
    long_term_target_value: UnsignedAmount | None
    current_equity_value: UnsignedAmount
    proposed_buy_total: UnsignedAmount
    max_new_buy: UnsignedAmount
    deployable_now: UnsignedAmount | None
    exception_applied: bool
    exception_missing: tuple[str, ...]
    violations: tuple[str, ...]
    warnings: tuple[AllocationWarning, ...]


def load_allocation_policy(path: Path = POLICY_PATH) -> AllocationPolicy:
    data, digest = load_pinned(path, PINNED_DIGESTS)
    policy = AllocationPolicy.model_validate(data)
    return policy.model_copy(update={"digest": digest})


def _s(value: Decimal) -> str:
    return format(value, "f")


def _diversification(policy: AllocationPolicy, positions: list[Position], capital: Decimal) -> list[str]:
    if any(p.industry is None or p.control_group_id is None for p in positions):
        return ["diversification_data_missing"]
    by_group, by_industry = defaultdict(Decimal), defaultdict(Decimal)
    for p in positions:
        by_group[p.control_group_id] += p.market_value
        by_industry[p.industry] += p.market_value
    rules = policy.exception
    found = []
    if sum(1 for v in by_group.values() if v > 0) < rules.min_issuers:
        found.append("too_few_issuers")
    if sum(1 for v in by_industry.values() if v > 0) < rules.min_industries:
        found.append("too_few_industries")
    if any(v > capital * rules.max_issuer for v in by_group.values()):
        found.append("issuer_concentration")
    if any(v > capital * rules.max_industry for v in by_industry.values()):
        found.append("industry_concentration")
    return found


def evaluate_allocation(policy: AllocationPolicy, *, capital: CapitalAssessment, risk: RiskAssessment, freshness: ProfileFreshness,
                        holdings: list[Position], buys: list[Position], exception: ExceptionReview | None = None,
                        exception_ratio: Decimal | None = None, available_cash: str | None = None,
                        now: datetime | None = None) -> AllocationDecision:
    now = now or datetime.now(timezone.utc)
    current = sum((p.market_value for p in holdings), Decimal(0))
    proposed = sum((p.market_value for p in buys), Decimal(0))
    violations, warnings, missing = [], [], ()
    base_ratio = policy.baseline_equity[risk.group]
    result = dict(status="blocked", policy_version=policy.version, risk_group=risk.group, current_equity_value=_s(current),
                  proposed_buy_total=_s(proposed), exception_applied=False, warnings=())

    if capital.status != "ready" or capital.investable_capital is None:
        return AllocationDecision(**result, target_ratio=None, current_ratio=None, long_term_target_value=None, max_new_buy="0",
                                  deployable_now=None, exception_missing=(), violations=("capital_not_ready",))
    total = capital.investable_capital
    if not risk.ready_for_allocation:
        violations.append("risk_needs_confirmation")
    if not freshness.allows_new_recommendations:
        violations.append("profile_reconfirm_required")

    target_ratio, applied = base_ratio, False
    if exception_ratio is not None:
        if risk.group not in policy.exception.eligible_groups:
            violations.append("exception_not_eligible")
        elif exception_ratio > policy.exception.max_equity:
            violations.append("exceeds_exception_cap")
        else:
            missing = review_exception(policy, exception, risk=risk, capital=capital, now=now)
            gaps = _diversification(policy, [*holdings, *buys], total)
            if missing:
                violations.append("exception_review_incomplete")
            violations.extend(gaps)
            if not missing and not gaps:
                target_ratio, applied = max(exception_ratio, base_ratio), True

    target_value = total * target_ratio
    headroom = max(target_value - current, Decimal(0))
    if risk.blocks_capital_increase:
        headroom = Decimal(0)
        if proposed:
            violations.append("capacity_blocks_increase")
    if current > target_value:
        warnings.append(AllocationWarning(code="above_target_from_price", amount=_s(current - target_value)))
    if proposed and current + proposed > target_value:
        violations.append("exceeds_target")
    if violations:
        headroom = Decimal(0)
    deployable = None if available_cash is None else min(headroom, Decimal(available_cash))
    return AllocationDecision(**{**result, "status": "blocked" if violations else "ok", "exception_applied": applied,
                                 "warnings": tuple(warnings)},
                              target_ratio=_s(target_ratio), current_ratio=_s(current / total),
                              long_term_target_value=_s(target_value), max_new_buy=_s(headroom),
                              deployable_now=None if deployable is None else _s(deployable),
                              exception_missing=missing, violations=tuple(dict.fromkeys(violations)))

