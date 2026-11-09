from signed_client import call
from test_deposit_book_route import client, save_layers

BOOK = {"accounts": [{"id": "a", "name": "TK", "amount": "100000000", "liquid": True}], "deposits": [], "bonds": [], "gold": [], "crypto": [], "count_ledger_cash": True, "reserve": None}
PLAN = {"id": "f", "name": "Quỹ", "asset": "fund", "day": 5, "start": "2027-01", "amount": "13000000"}


def test_a_purpose_is_saved_shown_and_leaves_the_tower_alone(tmp_path):
    c, clock = client(tmp_path)
    save_layers(c, clock)
    before = call(c, clock, "GET", "/internal/equity-budget").json()
    assert call(c, clock, "GET", "/internal/money-purposes").json()["version"] == 0
    r = call(c, clock, "PUT", "/internal/money-purposes", {"purposes": [{"id": "k", "name": "Cho con", "given": True}], "tags": {}, "expected_version": 0, "request_id": "mp1"})
    assert r.status_code == 200 and r.json()["version"] == 1 and r.json()["view"]["purposes"][0]["name"] == "Cho con"
    assert call(c, clock, "GET", "/internal/equity-budget").json() == before


def test_the_purposes_read_the_rows_of_the_book(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "PUT", "/internal/deposit-book", {**BOOK, "expected_version": 0, "request_id": "db1"}).status_code == 200
    body = call(c, clock, "PUT", "/internal/money-purposes", {"purposes": [{"id": "k", "name": "Cho con", "given": True}], "tags": {"a": "k"}, "expected_version": 0, "request_id": "mp1"}).json()
    assert body["view"]["given_total"] == "100000000" and body["rows"][0]["id"] == "a"


def test_an_unknown_purpose_and_a_stale_version_are_refused(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "PUT", "/internal/money-purposes", {"purposes": [], "tags": {"a": "x"}, "expected_version": 0, "request_id": "mp1"}).status_code == 422
    assert call(c, clock, "PUT", "/internal/money-purposes", {"purposes": [], "tags": {}, "expected_version": 0, "request_id": "mp2"}).status_code == 200
    assert call(c, clock, "PUT", "/internal/money-purposes", {"purposes": [], "tags": {}, "expected_version": 0, "request_id": "mp3"}).status_code == 409


def test_a_plan_and_a_buy_come_back_with_their_status(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/accumulation").json()["plans"] == []
    buy = {"id": "1", "plan": "f", "on": "2027-01-06", "amount": "13000000", "quantity": "500"}
    r = call(c, clock, "PUT", "/internal/accumulation", {"plans": [PLAN], "buys": [buy], "expected_version": 0, "request_id": "ac1"})
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == 1 and body["data"]["buys"][0]["quantity"] == "500" and body["plans"][0]["average"] == "26000" and body["plans"][0]["months"][0]["status"] == "met"


def test_a_buy_for_no_plan_is_refused_and_the_tower_is_left_alone(tmp_path):
    c, clock = client(tmp_path)
    save_layers(c, clock)
    before = call(c, clock, "GET", "/internal/equity-budget").json()
    assert call(c, clock, "PUT", "/internal/accumulation", {"plans": [], "buys": [{"id": "1", "plan": "x", "on": "2027-01-06", "amount": "1", "quantity": "1"}], "expected_version": 0, "request_id": "ac1"}).status_code == 422
    assert call(c, clock, "PUT", "/internal/accumulation", {"plans": [PLAN], "buys": [], "expected_version": 0, "request_id": "ac2"}).status_code == 200
    assert call(c, clock, "GET", "/internal/equity-budget").json() == before
