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


GOLD_PLAN = {"id": "g", "name": "Vàng", "asset": "gold", "day": 5, "start": "2027-01", "chi": "1"}
GOLD_BUY = {"id": "1", "plan": "g", "on": "2027-01-06", "amount": "10000000", "quantity": "1"}
GOLD_BOOK = {**BOOK, "accounts": [], "gold": [{"id": "r", "name": "Vàng", "amount": "30000000"}]}


def with_buy(c, clock):
    call(c, clock, "PUT", "/internal/accumulation", {"plans": [GOLD_PLAN], "buys": [GOLD_BUY], "expected_version": 0, "request_id": "ac1"})


def post(c, clock, version, rid, row="r", buy="1"):
    return call(c, clock, "POST", "/internal/accumulation/post", {"buy": buy, "row": row, "expected_version": version, "request_id": rid})


def test_a_buy_goes_into_the_book_once_and_is_marked(tmp_path):
    c, clock = client(tmp_path)
    call(c, clock, "PUT", "/internal/deposit-book", {**GOLD_BOOK, "expected_version": 0, "request_id": "db1"})
    with_buy(c, clock)
    view = call(c, clock, "GET", "/internal/accumulation").json()
    assert view["book_exists"] is True and view["plans"][0]["book_rows"] == [{"id": "r", "name": "Vàng"}]
    r = post(c, clock, 1, "acpost1")
    assert r.status_code == 200 and r.json()["data"]["buys"][0]["book_row"] == "r"
    book = call(c, clock, "GET", "/internal/deposit-book").json()
    assert book["book"]["gold"][0]["amount"] == "40000000" and book["version"] == 2
    again = post(c, clock, 2, "acpost2")
    assert again.status_code == 409 and again.json()["code"] == "already_posted"
    assert call(c, clock, "GET", "/internal/deposit-book").json()["book"]["gold"][0]["amount"] == "40000000"


def test_a_buy_is_not_posted_before_the_book_exists_since_that_would_empty_the_tower(tmp_path):
    c, clock = client(tmp_path)
    with_buy(c, clock)
    assert call(c, clock, "GET", "/internal/accumulation").json()["book_exists"] is False
    r = post(c, clock, 1, "acpost1", row=None)
    assert r.status_code == 422 and r.json()["code"] == "no_book"
    assert call(c, clock, "GET", "/internal/deposit-book").json()["version"] == 0


def test_an_unknown_buy_a_wrong_row_and_a_stale_version_are_refused(tmp_path):
    c, clock = client(tmp_path)
    call(c, clock, "PUT", "/internal/deposit-book", {**GOLD_BOOK, "expected_version": 0, "request_id": "db1"})
    with_buy(c, clock)
    assert post(c, clock, 1, "acpost1", buy="nope").status_code == 404
    assert post(c, clock, 1, "acpost2", row="nope").status_code == 422
    assert post(c, clock, 0, "acpost3").status_code == 409
    assert call(c, clock, "GET", "/internal/deposit-book").json()["version"] == 1
