from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client  # Clock date: 2027-01-15


def client():
    clock = Clock()
    return make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore())), clock


def save(c, clock, body, version=0, rid="wc1"):
    return call(c, clock, "PUT", "/internal/wealth-check", {**body, "expected_version": version, "request_id": rid})


def test_nothing_entered_yet():
    c, clock = client()
    assert call(c, clock, "GET", "/internal/wealth-check").json() == {"version": 0, "inputs": None, "check": None}


def test_saved_inputs_give_the_check_with_the_age_this_year():
    c, clock = client()
    assert save(c, clock, {"income": "25000000", "expenses": "17000000", "birth_year": 1989}).status_code == 200
    body = call(c, clock, "GET", "/internal/wealth-check").json()
    assert body["version"] == 1 and body["inputs"] == {"income": "25000000", "expenses": "17000000", "birth_year": 1989}
    assert body["check"]["age"] == 38 and body["check"]["target"] == "0.38" and body["check"]["status"] == "short"  # 2027


def test_bad_inputs_are_refused():
    c, clock = client()
    assert save(c, clock, {"income": "0", "expenses": "1", "birth_year": 1989}).status_code == 422
    assert save(c, clock, {"income": "-5", "expenses": "1", "birth_year": 1989}).status_code == 422
    assert save(c, clock, {"income": "10", "expenses": "1", "birth_year": 1850}).status_code == 422
    assert save(c, clock, {"income": "abc", "expenses": "1", "birth_year": 1989}).status_code == 422
