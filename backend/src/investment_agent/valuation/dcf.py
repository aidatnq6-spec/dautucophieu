"""Discounted cash flow with explicit forecast and Gordon terminal value kept separate."""

from decimal import Decimal
from typing import Literal

from investment_agent.domain.models import ContractModel, SignedAmount

from .assumptions import Scenario, ValuationAssumptions


class DiscountedValue(ContractModel):
    explicit: Decimal
    terminal: Decimal

    @property
    def total(self) -> Decimal:
        return self.explicit + self.terminal


class ScenarioValue(ContractModel):
    explicit: SignedAmount
    terminal: SignedAmount
    enterprise_value: SignedAmount | None  # FCFF only
    equity_value: SignedAmount
    per_share: SignedAmount


class ValuationResult(ContractModel):
    entity_id: str
    model: str
    status: Literal["draft", "approved", "unavailable"]
    reason: str | None = None
    buy_zone_active: bool
    content_digest: str
    scenarios: dict[str, ScenarioValue]


def _s(value: Decimal) -> str:
    return format(value, "f")


def discounted_value(s: Scenario, rate: Decimal | None = None) -> DiscountedValue:
    r = s.discount_rate if rate is None else rate
    if s.terminal_growth >= r:
        raise ValueError("terminal growth must be below the discount rate")
    factor = Decimal(1)
    explicit = Decimal(0)
    for flow in s.cash_flows:
        factor *= 1 + r
        explicit += flow / factor
    terminal = s.cash_flows[-1] * (1 + s.terminal_growth) / (r - s.terminal_growth) / factor
    return DiscountedValue(explicit=explicit, terminal=terminal)


def sensitivity(s: Scenario, rates: list[Decimal]) -> list[Decimal]:
    return [discounted_value(s, r).total for r in rates]


def value_assumptions(a: ValuationAssumptions) -> ValuationResult:
    from .dividends import ddm_value

    def result(status, scenarios, reason=None):
        return ValuationResult(entity_id=a.entity_id, model=a.model, status=status, reason=reason, scenarios=scenarios,
                               buy_zone_active=status == "approved", content_digest=a.content_digest)

    if a.shares is None:
        return result("unavailable", {}, "shares_missing")
    if a.model == "fcff_dcf" and a.net_debt is None:
        return result("unavailable", {}, "net_debt_missing")
    values = {}
    for name, s in a.scenarios.items():
        pv = ddm_value(s) if a.model == "ddm" else discounted_value(s)
        if a.model == "fcff_dcf":
            enterprise = pv.total
            equity = enterprise - a.net_debt - (a.minority_interest or 0) + (a.non_operating_assets or 0)
        else:
            enterprise, equity = None, pv.total + (a.non_operating_assets or 0)
        values[name] = ScenarioValue(explicit=_s(pv.explicit), terminal=_s(pv.terminal),
                                     enterprise_value=None if enterprise is None else _s(enterprise),
                                     equity_value=_s(equity), per_share=_s(equity / a.shares))
    return result(a.status, values)
