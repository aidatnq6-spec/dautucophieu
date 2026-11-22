"""Việc cuối năm on Năm tài chính (owner, 22/11/2026). The clock reads 15/01/2027: the list of 2026 is still open."""

from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client
from test_overview_route import setup_owner


def client():
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    setup_owner(c, clock)
    return c, clock


def test_the_list_shows_the_checks_and_the_owner_ticks_a_manual_item():
    c, clock = client()
    body = call(c, clock, "GET", "/internal/year-end").json()
    assert body["open"] is True and body["year"] == 2026 and body["version"] == 0
    assert [i["id"] for i in body["items"]] == ["theses", "tower", "calendar", "drill", "goals", "dividends", "cashflow"]
    assert next(i for i in body["items"] if i["id"] == "goals")["detail"] == "chưa đặt mục tiêu 2027"
    assert next(i for i in body["items"] if i["id"] == "drill")["done"] is None  # no data folder: not known, not "never drilled"
    ticked = call(c, clock, "POST", "/internal/year-end/tick", {"item": "dividends", "done": True, "expected_version": 0, "request_id": "y1"})
    assert ticked.status_code == 200 and next(i for i in ticked.json()["items"] if i["id"] == "dividends")["done"] is True
    refused = call(c, clock, "POST", "/internal/year-end/tick", {"item": "tower", "done": True, "expected_version": 1, "request_id": "y2"})
    assert refused.status_code == 422
    stale = call(c, clock, "POST", "/internal/year-end/tick", {"item": "cashflow", "done": True, "expected_version": 0, "request_id": "y3"})
    assert stale.status_code == 409


def test_the_year_review_reads_the_ledger_of_that_year_and_names_what_is_missing():
    from test_overview_route import buy_fpt
    c, clock = client()
    buy_fpt(c, clock)  # 100 tr deposited on 04/01/2027
    body = call(c, clock, "GET", "/internal/year-review/2027").json()
    assert body["year"] == 2027 and body["running"] is True and body["as_of"] == "2027-01-15"
    assert body["flows"]["deposits"] == "100000000" and body["flows"]["withdrawals"] == "0"
    assert body["contributions"] is None  # no Góp vốn đều plan
    assert body["cashflow"]["months"] == 0 and body["cashflow"]["missing"] == []  # January is not closed yet
    assert call(c, clock, "GET", "/internal/year-review/2010").status_code == 422


def test_goals_are_set_for_this_year_or_the_next_and_the_year_end_list_sees_them():
    c, clock = client()  # 15/01/2027
    assert call(c, clock, "GET", "/internal/year-goals/2027").json()["goals"] is None
    bad = call(c, clock, "PUT", "/internal/year-goals/2027", {"savings_rate": "1.5", "expected_version": 0, "request_id": "g0"})
    assert bad.status_code == 422
    saved = call(c, clock, "PUT", "/internal/year-goals/2027", {"contribution": "120000000", "savings_rate": "0.3", "expected_version": 0, "request_id": "g1"})
    assert saved.status_code == 200 and saved.json()["goals"] == {"contribution": "120000000", "savings_rate": "0.3"}
    goals = next(i for i in call(c, clock, "GET", "/internal/year-end").json()["items"] if i["id"] == "goals")
    assert goals["done"] is True  # the 2026 list: next year's goals are set
    assert call(c, clock, "GET", "/internal/year-goals/2029").status_code == 422
