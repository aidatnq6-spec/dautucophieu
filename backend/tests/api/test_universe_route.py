import pytest

from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client


@pytest.fixture
def store():
    return MemoryDocumentStore()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(store, clock):
    return make_client(clock, PersonalRepository("owner-1", store))


def candidates(n=50):
    return [{"entity_id": f"ent-{i:03d}", "ticker": f"T{i:02d}", "exchange": "HOSE", "industry": f"ind{i % 9}",
             "evidence": {"source": "verified_audit", "eligible": True, "live_eligible": True, "history_years": 10, "gaps": []},
             "metrics": {"as_of": "2027-01-14", "avg_matched_value_6m": "8000000000", "trading_session_ratio": "0.98",
                         "market_cap": "5000000000000"}} for i in range(n)]


def propose(client, clock, proposal_id="p1", n=50):
    return call(client, clock, "POST", "/internal/universe/proposals",
                {"proposal_id": proposal_id, "as_of": "2027-01-15", "candidates": candidates(n), "request_id": f"req-{proposal_id}"})


def decide(client, clock, proposal_id, decision, request_id):
    return call(client, clock, "POST", f"/internal/universe/proposals/{proposal_id}/{decision}", {"request_id": request_id})


def test_caller_supplied_evidence_never_qualifies(client, clock):
    body = propose(client, clock).json()
    assert body["members"] == []
    assert all("evidence_not_verified" in r["reasons"] for r in body["results"])


def test_proposal_does_not_change_active_until_approved(client, clock):
    propose(client, clock)
    assert call(client, clock, "GET", "/internal/universe").json() == {"version": 0, "active": None}
    approved = decide(client, clock, "p1", "approve", "a1").json()
    assert approved["version"] == 1 and approved["active"]["status"] == "incomplete"
    assert "target_50" in approved["active"]["gaps"]


def test_rejected_proposal_cannot_be_approved_later(client, clock):
    propose(client, clock)
    assert decide(client, clock, "p1", "reject", "r1").status_code == 200
    response = decide(client, clock, "p1", "approve", "a1")
    assert response.status_code == 409 and response.json()["code"] == "proposal_closed"
    assert call(client, clock, "GET", "/internal/universe").json()["active"] is None


def test_outdated_proposal_is_rejected_after_another_approval(client, clock):
    propose(client, clock, "p1")
    propose(client, clock, "p2")
    decide(client, clock, "p1", "approve", "a1")
    response = decide(client, clock, "p2", "approve", "a2")
    assert response.status_code == 409 and response.json()["code"] == "proposal_outdated"


def test_approval_retry_is_idempotent(client, clock):
    propose(client, clock)
    first = decide(client, clock, "p1", "approve", "a1").json()
    assert decide(client, clock, "p1", "approve", "a1").json()["version"] == first["version"] == 1


def test_unknown_proposal(client, clock):
    assert decide(client, clock, "nope", "approve", "a1").status_code == 404
