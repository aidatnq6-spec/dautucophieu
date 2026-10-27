from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client  # Clock date: 2027-01-15
from test_overview_route import buy_fpt, setup_owner  # ledger: 100 tr deposited on 2027-01-04


def client():
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    setup_owner(c, clock)
    buy_fpt(c, clock)
    return c, clock


def test_no_plan_yet_suggests_the_monthly_savings_from_the_wealth_check():
    c, clock = client()
    call(c, clock, "PUT", "/internal/wealth-check", {"income": "25000000", "expenses": "17000000", "birth_year": 1989, "expected_version": 0,
                                                     "request_id": "wc1"})
    body = call(c, clock, "GET", "/internal/contributions").json()
    assert body["plan"] is None and body["status"] is None and body["suggested_amount"] == "8000000"


def test_a_plan_reads_the_months_from_the_ledger():
    c, clock = client()
    saved = call(c, clock, "PUT", "/internal/contributions", {"amount": "50000000", "day": 4, "start": "2027-01", "expected_version": 0, "request_id": "cp1"})
    assert saved.status_code == 200
    s = call(c, clock, "GET", "/internal/contributions").json()["status"]
    assert [(m["month"], m["status"]) for m in s["months"]] == [("2027-01", "met")] and s["streak"] == 1 and s["contributed"] == "100000000"


def test_bad_plans_are_refused():
    c, clock = client()
    for body in ({"amount": "0", "day": 10, "start": "2027-01"}, {"amount": "1000", "day": 31, "start": "2027-01"},
                 {"amount": "1000", "day": 10, "start": "2027-13"}, {"amount": "abc", "day": 10, "start": "2027-01"}):
        assert call(c, clock, "PUT", "/internal/contributions", {**body, "expected_version": 0, "request_id": "cp2"}).status_code == 422
