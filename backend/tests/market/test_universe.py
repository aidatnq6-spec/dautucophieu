import json
from datetime import date

import pytest

from investment_agent.domain.pinned import InvalidPolicy
from investment_agent.market.universe import (
    POLICY_PATH, Candidate, UniverseError, approve, build_proposal, evaluate_candidate, load_universe_policy, research_scope,
)

AS_OF = date(2026, 10, 23)


@pytest.fixture(scope="module")
def policy():
    return load_universe_policy()


def candidate(i, **changes):
    data = {"entity_id": f"ent-{i:03d}", "ticker": f"T{i:02d}", "exchange": "HOSE", "industry": f"ind{i % 9}",
            "evidence": {"source": "verified_audit", "eligible": True, "live_eligible": True, "history_years": 10, "gaps": []},
            "metrics": {"as_of": "2026-10-23", "avg_matched_value_6m": "8000000000", "trading_session_ratio": "0.98",
                        "market_cap": "5000000000000"}}
    data.update(changes)
    return Candidate.model_validate(data)


def full(n=50, **changes):
    return [candidate(i, **changes) for i in range(n)]


def test_qualified_candidate_passes(policy):
    assert evaluate_candidate(policy, candidate(1), as_of=AS_OF).reasons == ()


@pytest.mark.parametrize("changes, reason", [
    ({"exchange": "HNX"}, "not_on_exchange"),
    ({"evidence": {"source": "verified_audit", "eligible": False, "live_eligible": False, "history_years": 7, "gaps": ["history"]}}, "coverage_not_eligible"),
    ({"evidence": {"source": "verified_audit", "eligible": True, "live_eligible": True, "history_years": 9, "gaps": []}}, "history_below_minimum"),
    ({"evidence": {"source": "caller_supplied", "eligible": True, "live_eligible": True, "history_years": 10, "gaps": []}}, "evidence_not_verified"),
    ({"evidence": {"source": "synthetic", "eligible": True, "live_eligible": True, "history_years": 10, "gaps": []}}, "evidence_not_verified"),
    ({"metrics": {"as_of": "2026-10-23", "avg_matched_value_6m": "4999999999", "trading_session_ratio": "0.98", "market_cap": "5000000000000"}}, "liquidity_below"),
    ({"metrics": {"as_of": "2026-10-23", "avg_matched_value_6m": "8000000000", "trading_session_ratio": "0.89", "market_cap": "5000000000000"}}, "sessions_below"),
    ({"metrics": {"as_of": "2026-10-23", "avg_matched_value_6m": "8000000000", "trading_session_ratio": "0.98", "market_cap": "1999999999999"}}, "market_cap_below"),
    ({"metrics": None}, "metrics_missing"),
    ({"metrics": {"as_of": "2026-08-01", "avg_matched_value_6m": "8000000000", "trading_session_ratio": "0.98", "market_cap": "5000000000000"}}, "metrics_stale"),
])
def test_failing_candidates_carry_reasons(policy, changes, reason):
    assert reason in evaluate_candidate(policy, candidate(1, **changes), as_of=AS_OF).reasons


def test_proposal_diff_against_active_version(policy):
    active = approve(policy, build_proposal(policy, "p1", full(), active=None, as_of=AS_OF), active=None, actor="owner")
    replacement = full(49) + [candidate(77)]
    proposal = build_proposal(policy, "p2", replacement, active=active, as_of=AS_OF)
    assert proposal.added == ("ent-077",) and proposal.removed == ("ent-049",)
    assert proposal.base_version == 1 and proposal.status == "draft"
    assert proposal.industry_counts["ind4"] == 5  # 4, 13, 22, 31, 40; 49 removed


def test_unapproved_proposal_does_not_change_active(policy):
    active = approve(policy, build_proposal(policy, "p1", full(), active=None, as_of=AS_OF), active=None, actor="owner")
    build_proposal(policy, "p2", full(49), active=active, as_of=AS_OF)
    assert active.version == 1 and len(active.members) == 50


def test_approving_49_is_not_a_full_universe(policy):
    approved = approve(policy, build_proposal(policy, "p1", full(49), active=None, as_of=AS_OF), active=None, actor="owner")
    assert approved.status == "incomplete" and not approved.complete
    assert "target_50" in approved.gaps


def test_full_verified_list_is_complete_only_under_confirmed_policy(policy):
    unconfirmed = approve(policy, build_proposal(policy, "p1", full(), active=None, as_of=AS_OF), active=None, actor="owner")
    assert unconfirmed.status == "incomplete" and unconfirmed.gaps == ("policy_unconfirmed",)
    confirmed = policy.model_copy(update={"status": "confirmed"})
    approved = approve(confirmed, build_proposal(confirmed, "p1", full(), active=None, as_of=AS_OF), active=None, actor="owner")
    assert approved.complete and len(approved.members) == 50


def test_one_failing_audit_blocks_complete_activation(policy):
    pool = full(49) + [candidate(49, exchange="HNX")]
    approved = approve(policy, build_proposal(policy, "p1", pool, active=None, as_of=AS_OF), active=None, actor="owner")
    assert approved.status == "incomplete" and "ent-049" not in approved.members


def test_duplicate_issuer_counts_once(policy):
    pool = full(49) + [candidate(0, ticker="DUP")]
    proposal = build_proposal(policy, "p1", pool, active=None, as_of=AS_OF)
    assert len(proposal.members) == 49


def test_scheduler_cannot_approve(policy):
    proposal = build_proposal(policy, "p1", full(), active=None, as_of=AS_OF)
    with pytest.raises(UniverseError) as error:
        approve(policy, proposal, active=None, actor="scheduler")
    assert error.value.code == "owner_approval_required"


def test_stale_proposal_cannot_be_approved_after_active_changed(policy):
    first = build_proposal(policy, "p1", full(), active=None, as_of=AS_OF)
    active = approve(policy, first, active=None, actor="owner")
    with pytest.raises(UniverseError) as error:
        approve(policy, first, active=active, actor="owner")
    assert error.value.code == "proposal_outdated"


def test_policy_change_invalidates_proposal(policy, tmp_path):
    proposal = build_proposal(policy, "p1", full(), active=None, as_of=AS_OF)
    other = policy.model_copy(update={"version": "universe-other"})
    with pytest.raises(UniverseError) as error:
        approve(other, proposal, active=None, actor="owner")
    assert error.value.code == "policy_changed"


def test_holdings_outside_universe_are_kept_but_not_researched(policy):
    active = approve(policy, build_proposal(policy, "p1", full(), active=None, as_of=AS_OF), active=None, actor="owner")
    scope = research_scope(active, holdings=["ent-001", "ent-999"], removed=["ent-777"])
    assert scope == {"ent-001": "research", "ent-999": "held_outside_universe", "ent-777": "removed_stop_buy"}


def test_policy_is_pinned(tmp_path):
    data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    data["min_market_cap"] = "1"
    path = tmp_path / "u.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InvalidPolicy):
        load_universe_policy(path)
