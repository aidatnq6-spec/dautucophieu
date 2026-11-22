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
