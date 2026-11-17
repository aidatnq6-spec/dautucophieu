from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client

PLAN = {"id": "p1", "name": "Tòa Mỹ Khê 10 phòng", "saved_on": "2026-11-17", "method": "annuity",
        "form": {"rooms": "10", "hiMonths": "5", "hiRent": "10.000.000"}, "rows": [{"name": "Điều hòa", "count": "10", "price": "12.000.000", "life": "8"}]}


def test_plans_are_saved_read_back_and_replaced_by_version():
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    assert call(c, clock, "GET", "/internal/settings/building-plans").json() == {"version": 0, "plans": []}
    saved = call(c, clock, "PUT", "/internal/settings/building-plans", {"plans": [PLAN], "expected_version": 0, "request_id": "b1"}).json()
    assert saved["version"] == 1 and saved["plans"][0]["name"] == "Tòa Mỹ Khê 10 phòng"
    assert call(c, clock, "GET", "/internal/settings/building-plans").json()["plans"][0]["form"]["hiRent"] == "10.000.000"
    stale = call(c, clock, "PUT", "/internal/settings/building-plans", {"plans": [], "expected_version": 0, "request_id": "b2"})
    assert stale.status_code == 409  # someone saved in between: not overwritten


def test_a_plan_list_out_of_bounds_is_refused():
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    too_many = [{**PLAN, "id": f"p{i}"} for i in range(21)]
    unnamed = [{**PLAN, "name": " "}]
    odd_key = [{**PLAN, "form": {"<script>": "1"}}]
    for plans in (too_many, unnamed, odd_key):
        assert call(c, clock, "PUT", "/internal/settings/building-plans", {"plans": plans, "expected_version": 0, "request_id": "b3"}).status_code == 422
