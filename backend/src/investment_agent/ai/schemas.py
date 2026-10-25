"""Model output contract: views and target weights with source references, never amounts or quantities."""

from typing import Literal

from pydantic import Field

from investment_agent.domain.models import ContractModel, NonemptyId, Ratio


class Opportunity(ContractModel):
    ticker: NonemptyId
    stance: Literal["accumulate", "hold", "watch", "reduce", "insufficient_basis"]
    target_weight: Ratio | None
    rationale: str = Field(min_length=1, max_length=1500)
    source_ids: tuple[NonemptyId, ...] = Field(min_length=1)


class AnalysisOutput(ContractModel):
    summary: str = Field(min_length=1, max_length=3000)
    market_view: str = Field(max_length=3000)
    opportunities: tuple[Opportunity, ...]
    risks: tuple[str, ...] = Field(min_length=1)
    source_ids: tuple[NonemptyId, ...]
