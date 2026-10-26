import json

from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client
from test_overview_route import MARKET, buy_fpt, setup_owner  # answers "C" → 39 điểm, balanced


def client():
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()), market=MARKET)
    setup_owner(c, clock)
    buy_fpt(c, clock)
    return c, clock


def override(c, clock, group, version, rid):
    return call(c, clock, "PUT", "/internal/risk/override", {"group": group, "expected_version": version, "request_id": rid})


def test_without_a_manual_group_the_survey_group_applies():
    c, clock = client()
    body = call(c, clock, "GET", "/internal/risk").json()
    assert body["override"] is None and body["effective"] == {"group": "balanced", "manual": False, "score_range": [34, 40], "equity_ratio": "0.35"}


def test_a_manual_group_shows_its_score_range_and_equity_ratio_and_keeps_the_survey():
    c, clock = client()
    assert override(c, clock, "strong_growth", 0, "ro1").status_code == 200
    body = call(c, clock, "GET", "/internal/risk").json()
    assert body["effective"] == {"group": "strong_growth", "manual": True, "score_range": [47, 52], "equity_ratio": "0.60"}
    assert body["assessment"]["group"] == "balanced" and body["override"]["version"] == 1


def test_the_manual_group_applies_everywhere():
    c, clock = client()
    override(c, clock, "strong_growth", 0, "ro1")
    call(c, clock, "PUT", "/internal/equity-budget", {"total": "1000000000", "expected_version": 0, "request_id": "eb1"})
    budget = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert budget["group"] == "strong_growth" and budget["budget"] == "600000000"
    overview = call(c, clock, "GET", "/internal/overview").json()
    assert overview["risk_group"] == "strong_growth"  # the group the recommendations and buy limits were computed with
    assert '"risk_group": "balanced"' not in json.dumps(overview)


def test_back_to_the_survey_result():
    c, clock = client()
    override(c, clock, "growth", 0, "ro1")
    assert override(c, clock, None, 1, "ro2").status_code == 200
    assert call(c, clock, "GET", "/internal/risk").json()["effective"]["group"] == "balanced"


def test_unknown_groups_are_refused():
    c, clock = client()
    assert override(c, clock, "yolo", 0, "ro1").status_code == 422
