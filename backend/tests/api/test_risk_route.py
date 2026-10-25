import pytest

from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client

ALL_C = [{"question": n, "answer": "C"} for n in range(1, 14)]
STOCK_RESERVE = {"as_of": "2027-01-15", "emergency_reserve": "200000000",
                 "assets": [{"asset_id": "stocks", "kind": "equity", "amount": "900000000", "liquidity": "liquid",
                             "earmarks": [{"purpose": "emergency", "amount": "200000000"}]}]}


@pytest.fixture
def store():
    return MemoryDocumentStore()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(store, clock):
    return make_client(clock, PersonalRepository("owner-1", store))


def save(client, clock, answers=ALL_C, *, confirmed=(), version=0, request_id="risk-1"):
    return call(client, clock, "PUT", "/internal/risk", {"answers": answers, "confirmed_conflicts": list(confirmed),
                                                         "expected_version": version, "request_id": request_id})


def test_questionnaire_is_served_with_version_and_notice(client, clock):
    body = call(client, clock, "GET", "/internal/risk/questionnaire").json()
    assert body["version"] == "risk-vi-2026-10-24.1" and len(body["questions"]) == 13
    assert "chưa được kiểm định" in body["notice"]


def test_saved_assessment_keeps_answers_score_flags_version_and_time(client, clock):
    response = save(client, clock)
    assert response.status_code == 200
    current = call(client, clock, "GET", "/internal/risk").json()
    assert current["version"] == 1 and current["assessed_at"].startswith("2027-01-15T08:00:00")
    assessment = current["assessment"]
    assert (assessment["total"], assessment["group"], len(assessment["answers"])) == (39, "balanced", 13)
    assert assessment["questionnaire_version"] == "risk-vi-2026-10-24.1" and assessment["flags"] == []
    assert current["profile_version"] is None


def test_stored_profile_conflict_is_detected_on_save(client, clock):
    preview = call(client, clock, "POST", "/internal/profile/assessment", {"profile": STOCK_RESERVE, "ledger_value": None}).json()
    call(client, clock, "PUT", "/internal/profile", {"profile": STOCK_RESERVE, "ledger_value": None, "reviewed_net": preview["net"],
                                                     "expected_version": 0, "request_id": "profile-1"})
    saved = save(client, clock).json()
    assert saved["profile_version"] == 1
    assert saved["assessment"]["unresolved_conflicts"] == ["profile_conflict_emergency"]
    assert saved["assessment"]["ready_for_allocation"] is False
    resolved = save(client, clock, confirmed=["profile_conflict_emergency"], version=1, request_id="risk-2").json()
    assert resolved["assessment"]["ready_for_allocation"] is True and resolved["version"] == 2


def test_invalid_answers_are_rejected_without_writing(client, clock, store):
    response = save(client, clock, ALL_C[:12])
    assert response.status_code == 422 and response.json()["code"] == "invalid_risk_answers"
    assert store.documents == {}


def test_preview_does_not_write(client, clock, store):
    response = call(client, clock, "POST", "/internal/risk/assessment", {"answers": ALL_C, "confirmed_conflicts": []})
    assert response.status_code == 200 and response.json()["group"] == "balanced"
    assert store.documents == {}


def test_version_conflict_and_unavailable_repository(client, clock, store):
    save(client, clock)
    assert save(client, clock, request_id="risk-2").json()["code"] == "version_conflict"
    store.available = False
    assert save(client, clock, version=1, request_id="risk-3").status_code == 503
    assert call(client, clock, "GET", "/internal/risk").status_code == 503
