"""Versioned 50-issuer research universe that changes only by owner approval.

Candidates pass on verified coverage evidence first, then liquidity. Evidence
supplied by a caller or a fixture never qualifies. A list short of the target,
or containing a failing audit, is recorded as incomplete and never becomes the
complete active universe. The research universe is separate from holdings:
owned positions outside it stay tracked but get no new buy research.
"""

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field

from investment_agent.domain.models import ContractModel, NonemptyId, Ratio, UnsignedAmount
from investment_agent.domain.pinned import CONFIG_DIR, load_pinned

POLICY_PATH = CONFIG_DIR / "universe-policy.json"
PINNED_DIGESTS = {
    "universe-2026-10-25.1": "a92fc5bb4bba2c75a0c7c4dd0f4f936c1fc1cf86a682c3702c0a384d6bfb8ce4",
    "universe-2026-10-27.1": "34735d03527f2e2daf194472a045fd668b7ec3e16112876beeb4973ff1a91454",
}


class UniverseError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class UniversePolicy(ContractModel):
    version: str
    digest: str = ""
    status: Literal["proposed_unconfirmed", "confirmed"]
    notice: str
    target_size: int = Field(strict=True, ge=1)
    exchange: str
    min_history_years: int = Field(strict=True, ge=1)
    min_avg_matched_value_6m: UnsignedAmount
    min_trading_session_ratio: Ratio
    min_market_cap: UnsignedAmount
    max_metrics_age_days: int = Field(strict=True, ge=1)
    history_exceptions: dict[str, str] = {}  # ticker -> why the owner keeps it despite a shorter history; waives only that rule


class CoverageEvidence(ContractModel):
    # Only server-side audits of licensed sources may produce "verified_audit".
    source: Literal["verified_audit", "caller_supplied", "synthetic"]
    eligible: bool
    live_eligible: bool
    history_years: int = Field(strict=True, ge=0)
    gaps: tuple[str, ...]


class CandidateMetrics(ContractModel):
    as_of: date
    avg_matched_value_6m: UnsignedAmount
    trading_session_ratio: Ratio
    market_cap: UnsignedAmount


class Candidate(ContractModel):
    entity_id: NonemptyId
    ticker: NonemptyId
    exchange: NonemptyId
    industry: NonemptyId
    evidence: CoverageEvidence
    metrics: CandidateMetrics | None


class CandidateResult(ContractModel):
    entity_id: NonemptyId
    ticker: NonemptyId
    industry: NonemptyId
    reasons: tuple[str, ...]


class Proposal(ContractModel):
    proposal_id: NonemptyId
    status: Literal["draft"] = "draft"
    policy_version: str
    as_of: date
    base_version: int = Field(strict=True, ge=0)
    members: tuple[NonemptyId, ...]
    results: tuple[CandidateResult, ...]
    added: tuple[NonemptyId, ...]
    removed: tuple[NonemptyId, ...]
    industry_counts: dict[str, int]


class UniverseVersion(ContractModel):
    version: int = Field(strict=True, ge=1)
    status: Literal["complete", "incomplete"]
    proposal_id: NonemptyId
    policy_version: str
    as_of: date
    members: tuple[NonemptyId, ...]
    gaps: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.status == "complete"


def load_universe_policy(path: Path = POLICY_PATH) -> UniversePolicy:
    data, digest = load_pinned(path, PINNED_DIGESTS)
    return UniversePolicy.model_validate(data).model_copy(update={"digest": digest})


def evaluate_candidate(policy: UniversePolicy, c: Candidate, *, as_of: date) -> CandidateResult:
    reasons = []
    if c.exchange != policy.exchange:
        reasons.append("not_on_exchange")
    if c.evidence.source != "verified_audit" or not c.evidence.live_eligible:
        reasons.append("evidence_not_verified")
    if not c.evidence.eligible:
        reasons.append("coverage_not_eligible")
    if c.evidence.history_years < policy.min_history_years and c.ticker not in policy.history_exceptions:
        reasons.append("history_below_minimum")
    m = c.metrics
    if m is None:
        reasons.append("metrics_missing")
    else:
        if not timedelta(0) <= as_of - m.as_of <= timedelta(days=policy.max_metrics_age_days):
            reasons.append("metrics_stale")
        if m.avg_matched_value_6m < policy.min_avg_matched_value_6m:
            reasons.append("liquidity_below")
        if m.trading_session_ratio < policy.min_trading_session_ratio:
            reasons.append("sessions_below")
        if m.market_cap < policy.min_market_cap:
            reasons.append("market_cap_below")
    return CandidateResult(entity_id=c.entity_id, ticker=c.ticker, industry=c.industry, reasons=tuple(reasons))


def build_proposal(policy: UniversePolicy, proposal_id: str, candidates: list[Candidate], *, active: UniverseVersion | None,
                   as_of: date) -> Proposal:
    results, seen = [], set()
    for c in candidates:
        if c.entity_id in seen:
            continue  # one issuer counts once even under several tickers
        seen.add(c.entity_id)
        results.append(evaluate_candidate(policy, c, as_of=as_of))
    passing = [r for r in results if not r.reasons]
    # Data conditions first, then liquidity rank; no industry quota.
    by_liquidity = {c.entity_id: c.metrics.avg_matched_value_6m for c in candidates if c.metrics}
    passing.sort(key=lambda r: (-by_liquidity.get(r.entity_id, Decimal(0)), r.entity_id))
    chosen = passing[:policy.target_size]
    members = tuple(sorted(r.entity_id for r in chosen))
    previous = set(active.members) if active else set()
    return Proposal(
        proposal_id=proposal_id, policy_version=policy.version, as_of=as_of, base_version=active.version if active else 0,
        members=members, results=tuple(results), added=tuple(sorted(set(members) - previous)),
        removed=tuple(sorted(previous - set(members))), industry_counts=dict(Counter(r.industry for r in chosen)),
    )


def approve(policy: UniversePolicy, proposal: Proposal, *, active: UniverseVersion | None,
            actor: Literal["owner", "scheduler"]) -> UniverseVersion:
    if actor != "owner":
        raise UniverseError("owner_approval_required")
    if proposal.policy_version != policy.version:
        raise UniverseError("policy_changed")
    if proposal.base_version != (active.version if active else 0):
        raise UniverseError("proposal_outdated")
    gaps = []
    if len(proposal.members) < policy.target_size:
        gaps.append(f"target_{policy.target_size}")
    if policy.status != "confirmed":
        gaps.append("policy_unconfirmed")
    return UniverseVersion(version=proposal.base_version + 1, status="incomplete" if gaps else "complete",
                           proposal_id=proposal.proposal_id, policy_version=policy.version, as_of=proposal.as_of,
                           members=proposal.members, gaps=tuple(gaps))


def research_scope(universe: UniverseVersion | None, *, holdings: list[str], removed: list[str] = ()) -> dict[str, str]:
    """Scope of owned and removed issuers; owned outside the universe are tracked, never researched for buys."""
    members = set(universe.members) if universe else set()
    scope = {e: "research" if e in members else "held_outside_universe" for e in holdings}
    scope.update({e: "removed_stop_buy" for e in removed})
    return scope
