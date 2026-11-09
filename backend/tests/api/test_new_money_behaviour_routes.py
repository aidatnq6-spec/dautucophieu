import base64
from datetime import date
from decimal import Decimal

from investment_agent.api.routes import ledger as ledger_route

from signed_client import call
from test_deposit_book_route import client, save_layers


def test_new_money_goes_to_the_short_layer_and_nothing_is_saved(tmp_path):
    c, clock = client(tmp_path)
    assert save_layers(c, clock).status_code == 200  # base 500 tr, risk 35%: stocks hold 5 tr at cost, 30% of 600 tr is 180 tr
    before = call(c, clock, "GET", "/internal/equity-budget").json()
    r = call(c, clock, "POST", "/internal/equity-budget/new-money", {"amount": "100000000"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["reserve_checked"] is False
    assert [(s["id"], s["why"], Decimal(s["amount"])) for s in body["steps"]] == [("stocks", "short", Decimal(100_000_000))]
    assert call(c, clock, "GET", "/internal/equity-budget").json() == before


def test_new_money_without_a_tower_says_why(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "POST", "/internal/equity-budget/new-money", {"amount": "100000000"}).json() == {"status": "no_total"}


def test_new_money_must_be_a_whole_positive_amount(tmp_path):
    c, clock = client(tmp_path)
    for bad in ("0", "1.5", "-1", "abc"):
        assert call(c, clock, "POST", "/internal/equity-budget/new-money", {"amount": bad}).status_code == 422


def orders_of(data, *, today):
    if data == b"bad":
        raise ledger_route.StatementFileError("Thiếu cột")
    return [{"symbol": "AAA", "date": date(2025, 1, 1), "type": "buy", "quantity": 10, "price": "1000", "fee": "1", "tax": "0", "order_no": "1", "line": 1}], [{"line": 7, "message": "AAA: lệnh chưa hoàn tất"}]


def enc(raw):
    return base64.b64encode(raw).decode()


def test_the_files_are_read_and_the_ledger_is_left_as_it_was(tmp_path, monkeypatch):
    c, clock = client(tmp_path)
    monkeypatch.setattr(ledger_route, "parse_tcbs_xlsx", orders_of)
    before = call(c, clock, "GET", "/internal/ledger").json()
    r = call(c, clock, "POST", "/internal/ledger/trade-behaviour", {"files": [{"name": "2025.xlsx", "content_base64": enc(b"a")}, {"name": "copy.xlsx", "content_base64": enc(b"b")}]})
    assert r.status_code == 200
    body = r.json()
    assert body["years"][0]["orders"] == 1 and body["duplicates"] == 1  # the same order in both files
    assert body["problems"][0] == {"file": "2025.xlsx", "line": 7, "message": "AAA: lệnh chưa hoàn tất"} and len(body["problems"]) == 2
    assert call(c, clock, "GET", "/internal/ledger").json() == before


def test_an_unreadable_file_is_named(tmp_path, monkeypatch):
    c, clock = client(tmp_path)
    monkeypatch.setattr(ledger_route, "parse_tcbs_xlsx", orders_of)
    r = call(c, clock, "POST", "/internal/ledger/trade-behaviour", {"files": [{"name": "x.xlsx", "content_base64": enc(b"bad")}]})
    assert r.status_code == 422 and "x.xlsx" in r.json()["message"]
