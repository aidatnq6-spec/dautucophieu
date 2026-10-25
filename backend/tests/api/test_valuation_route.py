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


SCENARIO = {"cash_flows": ["100", "110", "121"], "discount_rate": "0.10", "terminal_growth": "0"}
DRAFT = {"entity_id": "ent-fpt", "model": "fcff_dcf", "valuation_date": "2027-01-14",
         "scenarios": {"down": {**SCENARIO, "discount_rate": "0.12"}, "base": SCENARIO, "up": {**SCENARIO, "discount_rate": "0.09"}},
         "net_debt": "200", "shares": 10, "sources": ["doc-1"]}


def save(client, clock, draft=DRAFT, version=0, request_id="d1"):
    return call(client, clock, "PUT", "/internal/valuation/ent-fpt/draft", {"assumptions": draft, "expected_version": version, "request_id": request_id})


def test_draft_is_valued_but_not_active(client, clock):
    body = save(client, clock).json()
    assert body["version"] == 1 and body["assumptions"]["status"] == "draft"
    assert body["valuation"]["status"] == "draft" and body["valuation"]["buy_zone_active"] is False
    assert "E" not in body["valuation"]["scenarios"]["base"]["per_share"]


def test_approval_creates_immutable_version(client, clock):
    save(client, clock)
    body = call(client, clock, "POST", "/internal/valuation/ent-fpt/approve", {"draft_version": 1, "request_id": "a1"}).json()
    assert body["version"] == 2 and body["assumptions"]["status"] == "approved" and body["valuation"]["buy_zone_active"] is True
    assert body["assumptions"]["approved_at"].startswith("2027-01-15")


def test_approving_a_changed_draft_is_rejected(client, clock):
    save(client, clock)
    save(client, clock, {**DRAFT, "net_debt": "300"}, version=1, request_id="d2")
    response = call(client, clock, "POST", "/internal/valuation/ent-fpt/approve", {"draft_version": 1, "request_id": "a1"})
    assert response.status_code == 409 and response.json()["code"] == "draft_changed"


def test_client_cannot_submit_an_already_approved_payload(client, clock):
    response = save(client, clock, {**DRAFT, "status": "approved", "approved_at": "2027-01-15T00:00:00+00:00", "approved_by": "owner"})
    assert response.status_code == 422 and response.json()["code"] == "approval_via_endpoint_only"


def test_entity_mismatch_rejected(client, clock):
    response = save(client, clock, {**DRAFT, "entity_id": "ent-vnm"})
    assert response.status_code == 422 and response.json()["code"] == "entity_mismatch"


def test_new_draft_after_approval_leaves_approved_version_in_history(client, clock):
    save(client, clock)
    call(client, clock, "POST", "/internal/valuation/ent-fpt/approve", {"draft_version": 1, "request_id": "a1"})
    body = save(client, clock, {**DRAFT, "net_debt": "250"}, version=2, request_id="d2").json()
    assert body["version"] == 3 and body["valuation"]["buy_zone_active"] is False
    assert body["last_approved_version"] == 2


def test_approval_retry_returns_committed_approval(client, clock):
    save(client, clock)
    first = call(client, clock, "POST", "/internal/valuation/ent-fpt/approve", {"draft_version": 1, "request_id": "a1"}).json()
    clock.now += 30
    again = call(client, clock, "POST", "/internal/valuation/ent-fpt/approve", {"draft_version": 1, "request_id": "a1"})
    assert again.status_code == 200 and again.json()["assumptions"]["approved_at"] == first["assumptions"]["approved_at"]
