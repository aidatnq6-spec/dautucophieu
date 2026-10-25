"""Industry aggregates over the issuers we hold data for, always scoped as a sample."""

from decimal import Decimal
from statistics import median
from typing import Literal

from investment_agent.domain.models import ContractModel, NonemptyId


class IndustryAggregate(ContractModel):
    industry: NonemptyId
    metric: NonemptyId
    sample_count: int
    missing_count: int
    population: int | None  # issuers in the industry per an official list, if known
    coverage: Decimal | None
    median: Decimal | None
    members: tuple[NonemptyId, ...]
    # Computed from our sample only; an industry-wide claim needs an official statistic.
    claim_scope: Literal["sample_only"] = "sample_only"


def industry_aggregate(industry: str, metric: str, values: dict[str, Decimal | None], *, population: int | None) -> IndustryAggregate:
    present = {k: v for k, v in values.items() if v is not None}
    return IndustryAggregate(
        industry=industry, metric=metric, sample_count=len(present), missing_count=len(values) - len(present), population=population,
        coverage=Decimal(len(present)) / Decimal(population) if population else None,
        median=median(present.values()) if present else None, members=tuple(sorted(present)),
    )
