"""Allocation denominator: confirmed liquid capital after protected needs.

Ledger-tracked holdings are valued from the ledger, never from the declared
asset amount as well. Goals deduct only the shortfall left after funding
sources the owner has set aside; one source cannot fund more than it holds.
"""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from .models import ContractModel, NonemptyId, SignedAmount, UnsignedAmount

EMERGENCY = "emergency"
PROTECTION_MONTHS = 12


class Liquidity(str, Enum):
    LIQUID = "liquid"
    ILLIQUID = "illiquid"
    CONSUMPTION = "consumption"


class Earmark(ContractModel):
    purpose: NonemptyId
    amount: UnsignedAmount


class Asset(ContractModel):
    asset_id: NonemptyId
    kind: Literal["cash", "deposit", "bond", "fund", "equity", "real_estate", "other"]
    amount: UnsignedAmount
    liquidity: Liquidity
    ledger_link: NonemptyId | None = None
    earmarks: tuple[Earmark, ...] = ()


class FundingSource(ContractModel):
    source_id: NonemptyId
    amount: UnsignedAmount


class GoalFunding(ContractModel):
    source_id: NonemptyId
    amount: UnsignedAmount


class Goal(ContractModel):
    goal_id: NonemptyId
    due_date: date
    amount: UnsignedAmount
    funding: tuple[GoalFunding, ...] = ()
    preserve_capital: bool
    deferrable: bool
    confirmed: bool


class FinancialProfile(ContractModel):
    as_of: date
    emergency_reserve: UnsignedAmount
    assets: tuple[Asset, ...]
    goals: tuple[Goal, ...] = ()
    funding_sources: tuple[FundingSource, ...] = ()

    @model_validator(mode="after")
    def _consistent(self):
        for label, ids in (("asset", [a.asset_id for a in self.assets]), ("goal", [g.goal_id for g in self.goals]),
                           ("funding source", [s.source_id for s in self.funding_sources])):
            if any(count > 1 for count in Counter(ids).values()):
                raise ValueError(f"duplicate {label} id")
        goal_ids = {g.goal_id for g in self.goals}
        if EMERGENCY in goal_ids:
            raise ValueError("goal id is reserved")
        for item in self.assets:
            if sum((e.amount for e in item.earmarks), Decimal(0)) > item.amount:
                raise ValueError("earmarks exceed asset amount")
            if any(e.purpose != EMERGENCY and e.purpose not in goal_ids for e in item.earmarks):
                raise ValueError("earmark references unknown goal")
        capacity = {s.source_id: s.amount for s in self.funding_sources}
        used = defaultdict(Decimal)
        for item in self.goals:
            if sum((f.amount for f in item.funding), Decimal(0)) > item.amount:
                raise ValueError("funding exceeds goal amount")
            for funding in item.funding:
                if funding.source_id not in capacity:
                    raise ValueError("funding references unknown source")
                used[funding.source_id] += funding.amount
        if any(total > capacity[source] for source, total in used.items()):
            raise ValueError("funding source allocated beyond its amount")
        return self


class BreakdownLine(ContractModel):
    kind: Literal["included", "excluded", "deduction", "not_deducted"]
    ref: NonemptyId
    amount: UnsignedAmount
    reason: NonemptyId


class CapitalWarning(ContractModel):
    code: Literal["emergency_reserve_not_liquid", "emergency_reserve_shortfall"]
    amount: UnsignedAmount


class CapitalAssessment(ContractModel):
    status: Literal["ready", "not_suitable", "needs_confirmation", "incomplete"]
    investable_capital: UnsignedAmount | None = Field(description="None unless status is ready; never divide by it otherwise")
    shortfall: UnsignedAmount | None
    gross_included: UnsignedAmount
    deductions_total: UnsignedAmount
    net: SignedAmount
    lines: tuple[BreakdownLine, ...]
    warnings: tuple[CapitalWarning, ...]


def _s(value: Decimal) -> str:
    return format(value, "f")


def _protection_end(as_of: date) -> date:
    year = as_of.year + PROTECTION_MONTHS // 12
    try:
        return as_of.replace(year=year)
    except ValueError:  # 29 February
        return date(year, 2, 28)


def assess_capital(profile: FinancialProfile, *, ledger_value: Decimal | None) -> CapitalAssessment:
    """ledger_value: market value of cash, stocks and receivables tracked by the ledger, or None if unknown."""
    lines, warnings = [], []
    linked = False
    for item in profile.assets:
        if item.ledger_link is not None:
            linked = True
            lines.append(BreakdownLine(kind="excluded", ref=item.asset_id, amount=_s(item.amount), reason="counted_in_ledger"))
        elif item.liquidity is not Liquidity.LIQUID:
            lines.append(BreakdownLine(kind="excluded", ref=item.asset_id, amount=_s(item.amount), reason=f"{item.liquidity.value}_asset"))
        else:
            lines.append(BreakdownLine(kind="included", ref=item.asset_id, amount=_s(item.amount), reason="liquid_asset"))
    if ledger_value is not None:
        lines.append(BreakdownLine(kind="included", ref="ledger", amount=_s(ledger_value), reason="ledger_market_value"))

    protected = not_liquid = Decimal(0)
    for item in profile.assets:
        reserved = sum((e.amount for e in item.earmarks if e.purpose == EMERGENCY), Decimal(0))
        if item.kind == "equity" or item.ledger_link is not None or item.liquidity is not Liquidity.LIQUID:
            not_liquid += reserved
        else:
            protected += reserved
    if not_liquid:
        warnings.append(CapitalWarning(code="emergency_reserve_not_liquid", amount=_s(not_liquid)))
    if protected < profile.emergency_reserve:
        warnings.append(CapitalWarning(code="emergency_reserve_shortfall", amount=_s(profile.emergency_reserve - protected)))
    if profile.emergency_reserve:
        lines.append(BreakdownLine(kind="deduction", ref=EMERGENCY + "_reserve", amount=_s(profile.emergency_reserve), reason="emergency_reserve"))

    end = _protection_end(profile.as_of)
    for item in profile.goals:
        need = item.amount - sum((f.amount for f in item.funding), Decimal(0))
        if not need:
            continue
        if item.due_date <= end:
            lines.append(BreakdownLine(kind="deduction", ref=item.goal_id, amount=_s(need), reason="due_within_12_months"))
        elif item.preserve_capital or not item.deferrable:
            lines.append(BreakdownLine(kind="deduction", ref=item.goal_id, amount=_s(need),
                                       reason="capital_preservation" if item.preserve_capital else "not_deferrable"))
        else:
            lines.append(BreakdownLine(kind="not_deducted", ref=item.goal_id, amount=_s(need), reason="flexible_beyond_12_months"))

    gross = sum((line.amount for line in lines if line.kind == "included"), Decimal(0))
    deductions = sum((line.amount for line in lines if line.kind == "deduction"), Decimal(0))
    net = gross - deductions
    if linked and ledger_value is None:
        status = "incomplete"
    elif not all(item.confirmed for item in profile.goals):
        status = "needs_confirmation"
    elif net <= 0:
        status = "not_suitable"
    else:
        status = "ready"
    return CapitalAssessment(
        status=status, investable_capital=_s(net) if status == "ready" else None,
        shortfall=_s(Decimal(0) - net) if status == "not_suitable" else None, gross_included=_s(gross),
        deductions_total=_s(deductions), net=_s(net), lines=tuple(lines), warnings=tuple(warnings),
    )
