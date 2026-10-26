from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client


def test_defaults_then_owner_update(tmp_path):
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    got = call(c, clock, "GET", "/internal/settings/valuation").json()
    assert got == {"version": 0, "settings": {"required_return": "0.13", "long_term_growth": "0.05", "threshold": "0.2"}}
    body = {"settings": {"required_return": "0.14", "long_term_growth": "0.05", "threshold": "0.15"}, "expected_version": 0, "request_id": "v1"}
    assert call(c, clock, "PUT", "/internal/settings/valuation", body).json()["version"] == 1
    assert call(c, clock, "GET", "/internal/settings/valuation").json()["settings"]["threshold"] == "0.15"


def test_required_return_must_exceed_growth_and_threshold_must_be_sensible():
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    for bad in ({"required_return": "0.05", "long_term_growth": "0.05", "threshold": "0.2"},
                {"required_return": "0.13", "long_term_growth": "0.05", "threshold": "0"}):
        assert call(c, clock, "PUT", "/internal/settings/valuation", {"settings": bad, "expected_version": 0, "request_id": "v2"}).status_code == 422
