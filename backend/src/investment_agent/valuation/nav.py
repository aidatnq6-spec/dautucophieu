"""Adjusted NAV for project-based issuers (real estate, industrial parks).

Each project contributes ownership × probability × (gross value − its own
obligations). Corporate net debt is supplied excluding those project
obligations, so nothing is deducted twice. Missing project data makes the
model unavailable; it is never replaced by book value or a P/B shortcut.
"""

from decimal import Decimal
from typing import Literal

from pydantic import Field

from investment_agent.domain.models import ContractModel, NonemptyId, Ratio, SignedAmount, UnsignedAmount

from .common import ApprovalRef, SectorResult, finish, s


class Project(ContractModel):
    project_id: NonemptyId
    ownership: Ratio
    probability: Ratio  # legal and progress risk, owner-approved
    legal_status: Literal["approved", "pending", "disputed", "unknown"]
    progress_note: str
    gross_value: UnsignedAmount | None  # PV of project cash flows before project obligations
    project_obligations: UnsignedAmount


class ProjectContribution(ContractModel):
    project_id: NonemptyId
    contribution: SignedAmount


class NavInputs(ApprovalRef):
    projects: tuple[Project, ...]
    corporate_net_debt_excluding_project_obligations: SignedAmount
    other_assets: UnsignedAmount
    minority_interest: UnsignedAmount
    shares: int | None = Field(default=None, strict=True, gt=0)


class NavResult(SectorResult):
    projects: tuple[ProjectContribution, ...] = ()


def value_nav(i: NavInputs) -> NavResult:
    if not i.projects or any(p.gross_value is None for p in i.projects):
        return NavResult(**finish("nav", i, None, i.shares, reason="project_data_missing"))
    rows = [ProjectContribution(project_id=p.project_id, contribution=s(p.ownership * p.probability * (p.gross_value - p.project_obligations)))
            for p in i.projects]
    equity = sum((r.contribution for r in rows), Decimal(0)) + i.other_assets - i.corporate_net_debt_excluding_project_obligations - i.minority_interest
    flags = ["disputed_project"] if any(p.legal_status == "disputed" for p in i.projects) else []
    return NavResult(**finish("nav", i, equity, i.shares, flags=flags, reason=None if i.shares else "shares_missing"), projects=tuple(rows))
