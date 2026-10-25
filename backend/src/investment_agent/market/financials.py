"""Reported financial facts with scope, period type, unit and publication time kept explicit."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, model_validator

from investment_agent.domain.models import ContractModel, NonemptyId, SignedAmount

UNIT_SCALE = {"VND": Decimal(1), "thousand_VND": Decimal(1000), "million_VND": Decimal(1_000_000), "shares": Decimal(1)}


class FinancialFact(ContractModel):
    entity_id: NonemptyId
    metric: Literal["net_income_parent", "equity_parent", "shares_outstanding", "revenue", "operating_cash_flow", "net_debt"]
    period_type: Literal["quarter", "annual"]
    fiscal_label: NonemptyId
    period_end: date
    statement_scope: Literal["consolidated", "separate"]
    value: SignedAmount
    unit: Literal["VND", "thousand_VND", "million_VND", "shares"]
    published_at: AwareDatetime | None = None
    published_date: date | None = None  # date-only disclosures
    revision_id: NonemptyId
    source_id: NonemptyId
    provenance_mode: Literal["synthetic", "historical_as_reported", "latest_restated"]
    derived: bool = False  # e.g. Q4 = full year minus 9 months

    @model_validator(mode="after")
    def _normalise(self):
        if self.published_at is not None and self.published_date is not None:
            raise ValueError("give published_at or published_date, not both")
        if self.metric == "shares_outstanding" and self.unit not in {"shares", "VND"}:
            raise ValueError("share counts are not monetary")
        if self.unit not in {"VND", "shares"}:
            # Set directly so the validator does not run again on the normalised value.
            object.__setattr__(self, "value", self.value * UNIT_SCALE[self.unit])
            object.__setattr__(self, "unit", "VND")
        return self
