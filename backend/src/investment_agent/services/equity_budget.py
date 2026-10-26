"""Vốn dành cho cổ phiếu: the owner's total financial assets (one number, `settings/equity_budget`), less the emergency reserve and
needs due within 12 months from the confirmed profile, times the equity ratio of the risk group. Personal data; never sent to a model."""

from decimal import Decimal

from investment_agent.domain.allocation import load_allocation_policy
from investment_agent.domain.equity_budget import equity_budget
from investment_agent.domain.ledger import replay
from investment_agent.domain.profile import ConfirmedProfile
from investment_agent.services.records import LedgerBook, StoredRisk, effective_risk, read_current, read_version

RECORD = ("settings", "equity_budget")
PROTECTED = {"emergency_reserve", "due_within_12_months"}


def budget_view(repo, owner) -> tuple[dict, int]:
    """(budget, version of the stored total); raises RepositoryUnavailable."""
    stored = read_version(repo, owner, *RECORD, None)
    if stored is None:
        return {"status": "no_total"}, 0
    profile, _ = read_current(repo, owner, "profile_versions", "main")
    risk, _ = read_current(repo, owner, "risk_versions", "main")
    lines = ConfirmedProfile.model_validate(profile.payload).assessment.lines if profile else ()
    deductions = sum((line.amount for line in lines if line.kind == "deduction" and line.reason in PROTECTED), Decimal(0))
    effective = effective_risk(repo, owner, StoredRisk.model_validate(risk.payload).assessment if risk else None)
    group = effective.group if effective else None
    positions = replay(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)).positions
    held_cost = sum((p.total_cost for p in positions if p.quantity + p.pending_quantity > 0), Decimal(0))
    budget = equity_budget(total=Decimal(stored.payload["total"]), deductions=deductions, group=group,
                           ratios=dict(load_allocation_policy().baseline_equity), held_cost=held_cost)
    return budget, stored.version
