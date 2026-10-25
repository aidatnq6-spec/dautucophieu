"""Valuation assumptions: three scenarios, an explicit model choice, owner approval.

FCFF values the firm, so net debt and minority interest are subtracted once
and non-operating assets added; FCFE and DDM already value equity and must not
carry net debt. FCFE may add non-operating assets excluded from its flows; DDM
may not, since dividends are paid from all assets. Only an owner-approved,
immutable version may activate a buy zone; a draft is valued but labelled draft.
"""

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, ConfigDict, Field, model_validator

from investment_agent.domain.models import ContractModel, NonemptyId, Ratio, SignedAmount, UnsignedAmount
from investment_agent.domain.pinned import content_digest as _digest


class AssumptionError(ValueError):
    pass


class Scenario(ContractModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cash_flows: tuple[SignedAmount, ...] = Field(min_length=1, description="Explicit forecast, year 1..N, VND")
    discount_rate: Ratio
    terminal_growth: SignedAmount

    @model_validator(mode="after")
    def _terminal(self):
        if self.discount_rate <= 0:
            raise ValueError("discount rate must be positive")
        if self.terminal_growth >= self.discount_rate:
            raise ValueError("terminal growth must be below the discount rate")
        return self


class ValuationAssumptions(ContractModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_id: NonemptyId
    model: Literal["fcff_dcf", "fcfe_dcf", "ddm"]
    valuation_date: date
    scenarios: dict[Literal["down", "base", "up"], Scenario]
    net_debt: SignedAmount | None = None
    minority_interest: UnsignedAmount | None = None
    non_operating_assets: UnsignedAmount | None = None
    shares: int | None = Field(default=None, strict=True, gt=0)
    reinvestment_note: str = ""
    sources: tuple[NonemptyId, ...] = ()
    status: Literal["draft", "approved"] = "draft"
    approved_at: AwareDatetime | None = None
    approved_by: str | None = None

    @model_validator(mode="after")
    def _consistent(self):
        if set(self.scenarios) != {"down", "base", "up"}:
            raise ValueError("down, base and up scenarios are all required")
        if self.model != "fcff_dcf" and (self.net_debt is not None or self.minority_interest is not None):
            raise ValueError("equity models already net out debt; do not supply net debt or minority interest")
        if self.model == "ddm" and self.non_operating_assets is not None:
            raise ValueError("dividends already reflect all assets; adding non-operating assets double counts")
        if (self.status == "approved") != (self.approved_at is not None):
            raise ValueError("approval fields inconsistent")
        return self

    @property
    def content_digest(self) -> str:
        return _digest(self.model_dump(mode="json", exclude={"status", "approved_at", "approved_by"}))


def approve_assumptions(a: ValuationAssumptions, *, actor: str, now) -> ValuationAssumptions:
    if actor != "owner":
        raise AssumptionError("owner_approval_required")
    if a.status == "approved":
        raise AssumptionError("already_approved")
    return ValuationAssumptions.model_validate({**a.model_dump(mode="json"), "status": "approved",
                                               "approved_at": now.isoformat(), "approved_by": "owner"})
