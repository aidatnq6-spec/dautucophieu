import pytest

from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import DAY, Clock, call, make_client

PROFILE = {"as_of": "2027-01-15", "emergency_reserve": "200000000",
           "assets": [{"asset_id": "savings", "kind": "deposit", "amount": "800000000", "liquidity": "liquid",
                       "earmarks": [{"purpose": "emergency", "amount": "200000000"}]}],
           "goals": [{"goal_id": "tuition", "due_date": "2027-09-01", "amount": "100000000",
                      "preserve_capital": False, "deferrable": False, "confirmed": True}]}


@pytest.fixture
def store():
    return MemoryDocumentStore()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(store, clock):
    return make_client(clock, PersonalRepository("owner-1", store))


def save(client, clock, *, reviewed="500000000", version=0, request_id="req-1", profile=PROFILE):
    return call(client, clock, "PUT", "/internal/profile", {"profile": profile, "ledger_value": None,
                "reviewed_net": reviewed, "expected_version": version, "request_id": request_id})


def test_assessment_preview_returns_breakdown_without_writing(client, clock, store):
    response = call(client, clock, "POST", "/internal/profile/assessment", {"profile": PROFILE, "ledger_value": None})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready" and body["investable_capital"] == "500000000"
    assert {line["ref"] for line in body["lines"] if line["kind"] == "deduction"} == {"emergency_reserve", "tuition"}
    assert store.documents == {}


def test_confirmed_profile_is_versioned_and_readable(client, clock):
    response = save(client, clock)
    assert response.status_code == 200 and response.json()["version"] == 1
    current = call(client, clock, "GET", "/internal/profile").json()
    assert current["version"] == 1 and current["assessment"]["investable_capital"] == "500000000"
    assert current["freshness"]["status"] == "current" and current["stale"] is False
    assert current["confirmed_at"].startswith("2027-01-15T08:00:00")


def test_reviewed_capital_must_match_current_breakdown(client, clock, store):
    response = save(client, clock, reviewed="600000000")
    assert response.status_code == 409 and response.json()["code"] == "capital_changed"
    assert store.documents == {}


def test_unconfirmed_goal_cannot_be_saved_as_confirmed_profile(client, clock, store):
    draft = {**PROFILE, "goals": [{**PROFILE["goals"][0], "confirmed": False}]}
    response = save(client, clock, profile=draft, reviewed=None)
    assert response.status_code == 422 and response.json()["code"] == "profile_not_confirmable"
    assert store.documents == {}


def test_not_suitable_profile_can_be_confirmed_for_asset_reporting(client, clock):
    poor = {**PROFILE, "emergency_reserve": "800000000",
            "assets": [{**PROFILE["assets"][0], "earmarks": [{"purpose": "emergency", "amount": "800000000"}]}]}
    response = save(client, clock, profile=poor, reviewed="-100000000")
    assert response.status_code == 200 and response.json()["assessment"]["status"] == "not_suitable"


def test_stale_version_and_retry_semantics(client, clock):
    assert save(client, clock).status_code == 200
    assert save(client, clock).json()["version"] == 1  # same request retried
    conflict = save(client, clock, request_id="req-2", version=0)
    assert conflict.status_code == 409 and conflict.json()["code"] == "version_conflict"
    assert save(client, clock, request_id="req-2", version=1).json()["version"] == 2


def test_old_profile_requires_reconfirmation_but_still_reads(client, clock):
    save(client, clock)
    clock.now += 32 * DAY
    current = call(client, clock, "GET", "/internal/profile").json()
    assert current["freshness"] == {"status": "reconfirm_required", "allows_new_recommendations": False, "allows_asset_report": True}


def test_missing_profile_and_unavailable_repository(client, clock, store):
    assert call(client, clock, "GET", "/internal/profile").json()["code"] == "profile_missing"
    store.available = False
    response = call(client, clock, "GET", "/internal/profile")
    assert response.status_code == 503 and response.json()["code"] == "personal_repository_unavailable"


def test_unconfigured_repository_fails_closed(clock):
    assert save(make_client(clock), clock).status_code == 503


def test_validation_errors_do_not_echo_personal_amounts(client, clock):
    bad = {**PROFILE, "emergency_reserve": 123456789.5}
    response = call(client, clock, "POST", "/internal/profile/assessment", {"profile": bad, "ledger_value": None})
    assert response.status_code == 422 and response.json()["code"] == "invalid_request"
    assert "123456789" not in response.text and "800000000" not in response.text


def test_profile_routes_require_signed_owner_context(client):
    assert client.get("/internal/profile").status_code == 401
