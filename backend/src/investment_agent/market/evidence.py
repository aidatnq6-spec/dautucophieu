"""Governance evidence and the per-entity analysis pack.

Evidence is official (a regulator or court decision), disputed (contested,
with the company response when found) or unverified (press, AI assessment).
Finding nothing in the sources checked is reported as exactly that; it is never
turned into a statement about integrity.
"""

from collections import Counter
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from investment_agent.domain.models import ContractModel, NonemptyId

from .industry import IndustryAggregate
from .macro import MacroObservation, MacroVintages


class GovernanceEvidence(ContractModel):
    evidence_id: NonemptyId
    entity_id: NonemptyId
    topic: Literal["audit", "disclosure", "related_party", "insider", "sanction", "leadership_change"]
    classification: Literal["official", "disputed", "unverified"]
    summary: NonemptyId
    source_url: str = Field(pattern=r"^https://\S+$")
    event_date: date
    company_response: str | None
    assessed_by_ai: bool


class GovernanceSummary(ContractModel):
    entity_id: NonemptyId
    status: Literal["not_checked", "no_records_found_in_sources_checked", "findings_recorded"]
    sources_checked: tuple[str, ...]
    counts: dict[str, int]
    findings: tuple[GovernanceEvidence, ...]
    ai_assessed_ids: tuple[str, ...]


def governance_summary(entity_id: str, items: list[GovernanceEvidence], *, sources_checked: list[str]) -> GovernanceSummary:
    mine = [e for e in items if e.entity_id == entity_id]
    if mine:
        status = "findings_recorded"
    else:
        status = "no_records_found_in_sources_checked" if sources_checked else "not_checked"
    return GovernanceSummary(entity_id=entity_id, status=status, sources_checked=tuple(sources_checked),
                             counts=dict(Counter(e.classification for e in mine)),
                             findings=tuple(sorted(mine, key=lambda e: e.event_date)),
                             ai_assessed_ids=tuple(e.evidence_id for e in mine if e.assessed_by_ai))


class AnalysisPack(ContractModel):
    entity_id: NonemptyId
    industry: NonemptyId
    as_of: datetime
    macro_facts: tuple[MacroObservation, ...]
    industry_facts: tuple[IndustryAggregate, ...]
    governance: GovernanceSummary
    gaps: tuple[str, ...]


def build_analysis_pack(entity_id: str, *, industry: str, macro: MacroVintages, macro_series: list[str], period: str,
                        as_of: datetime, industry_aggregates: list[IndustryAggregate], governance: GovernanceSummary) -> AnalysisPack:
    facts, gaps = [], []
    for series in macro_series:
        obs = macro.as_of(series, period, as_of)
        if obs is None:
            gaps.append(f"macro_missing:{series}")
        else:
            facts.append(obs)
    aggregates = [a for a in industry_aggregates if a.industry == industry]
    for a in aggregates:
        if a.coverage is None:
            gaps.append(f"industry_coverage_unknown:{a.metric}")
        if a.sample_count == 0:
            gaps.append(f"industry_no_data:{a.metric}")
    if not aggregates:
        gaps.append("industry_missing")
    if governance.status == "not_checked":
        gaps.append("governance_not_checked")
    return AnalysisPack(entity_id=entity_id, industry=industry, as_of=as_of, macro_facts=tuple(facts),
                        industry_facts=tuple(aggregates), governance=governance, gaps=tuple(gaps))
