from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.leading import MacroStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_overview_route import MARKET, buy_fpt, setup_owner  # Cân bằng 35%; ledger: 95 tr cash, FPT 5 tr at cost; today 2027-01-15

DEPOSITS = [{"id": "a", "bank": "Ngân hàng A", "matures": "2027-02-05", "principal": "200000000", "rate": "6", "interest": "2000000",
             "payout": "end", "locked": True},
            {"id": "b", "bank": "Ngân hàng B", "matures": "2027-01-10", "principal": "100000000", "rate": None, "interest": None,
             "payout": "upfront", "locked": False}]
ACCOUNTS = [{"id": "x", "name": "Tài khoản thanh toán", "amount": "10000000", "liquid": True},
            {"id": "y", "name": "Ví chưa rút", "amount": "5000000", "liquid": False}]


def client(tmp_path):
    MacroStore(tmp_path).upsert("deposit_12m", [(date(2027, 1, 14), "5")], entry="auto")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=MARKET, data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    setup_owner(c, clock)
    buy_fpt(c, clock)
    return c, clock


def save_book(c, clock, deposits=DEPOSITS, accounts=ACCOUNTS, version=0, rid="db1"):
    return call(c, clock, "PUT", "/internal/deposit-book", {"deposits": deposits, "accounts": accounts, "expected_version": version, "request_id": rid})


def save_layers(c, clock, version=0):
    return call(c, clock, "PUT", "/internal/equity-budget", {"layers": {"deposit": "300000000", "bond": "0", "gold": "100000000", "crypto": "0"},
                                                            "reserve": "120000000", "expected_version": version, "request_id": "eb1"})


def test_an_empty_book_has_no_rows_and_liquidity_from_the_ledger_cash(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/deposit-book").json()
    assert body["version"] == 0 and body["book"] == {"accounts": [], "deposits": [], "count_ledger_cash": True}
    assert body["liquidity"]["now"] == "95000000" and body["calendar"]["months"] == []


def test_saved_book_gives_the_calendar_and_liquidity_against_the_reserve_of_the_pyramid(tmp_path):
    c, clock = client(tmp_path)
    save_layers(c, clock)
    ok = save_book(c, clock)
    assert ok.status_code == 200
    body = call(c, clock, "GET", "/internal/deposit-book").json()
    assert body["version"] == 1 and [d["id"] for d in body["book"]["deposits"]] == ["a", "b"]
    assert body["calendar"]["months"] == [{"month": "2027-02", "count": 1, "principal": "200000000", "interest": "2000000", "missing_interest": 0}]
    assert body["calendar"]["due_soon"] == ["a"] and body["calendar"]["overdue"] == ["b"]
    l = body["liquidity"]
    assert l["now"] == "105000000" and l["reserve"] == "120000000" and l["status"] == "short" and l["short"] == "15000000"
    assert l["not_now"] == {"accounts": "5000000", "locked": "200000000", "unlocked": "0", "overdue": "100000000"}


def test_the_pyramid_takes_deposits_and_cash_accounts_from_the_book(tmp_path):
    c, clock = client(tmp_path)
    save_layers(c, clock)
    before = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert before["deposit_source"] == "manual"
    save_book(c, clock)
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    amounts = {l["id"]: l["amount"] for l in b["pyramid"]["layers"]}
    assert amounts["deposit"] == "300000000" and amounts["cash"] == "110000000"  # 200 + 100 tr in sổ; 95 ledger + 15 accounts
    assert b["deposit_source"] == "book" and b["total"] == "635000000"  # 120 + 110 + 300 + 100 gold + 5 stocks


def test_only_cash_accounts_keep_the_hand_entered_deposits(tmp_path):
    c, clock = client(tmp_path)
    save_layers(c, clock)
    save_book(c, clock, deposits=[])
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    amounts = {l["id"]: l["amount"] for l in b["pyramid"]["layers"]}
    assert b["deposit_source"] == "manual" and amounts["deposit"] == "300000000" and amounts["cash"] == "110000000"


def test_passive_income_uses_each_deposit_rate_and_counts_those_on_the_market_rate(tmp_path):
    c, clock = client(tmp_path)
    save_layers(c, clock)
    save_book(c, clock)
    income = call(c, clock, "GET", "/internal/passive-income").json()["income"]
    assert income["deposit"] == "1416667"  # 200 tr × 6% / 12 + 100 tr × 5% (market) / 12
    assert income["deposit_market_rate_count"] == 1


def test_invalid_books_and_stale_versions_are_refused(tmp_path):
    c, clock = client(tmp_path)
    assert save_book(c, clock, deposits=[{**DEPOSITS[0], "principal": "-1"}]).status_code == 422
    assert save_book(c, clock, deposits=[DEPOSITS[0], DEPOSITS[0]]).status_code == 422
    assert save_book(c, clock).status_code == 200
    assert save_book(c, clock, version=0, rid="db2").status_code == 409


def test_cash_from_the_book_only_leaves_the_ledger_cash_out_of_the_pyramid_and_cash_now(tmp_path):
    c, clock = client(tmp_path)
    save_layers(c, clock)
    ok = call(c, clock, "PUT", "/internal/deposit-book", {"deposits": DEPOSITS, "accounts": ACCOUNTS, "count_ledger_cash": False,
                                                         "expected_version": 0, "request_id": "db1"})
    assert ok.status_code == 200 and ok.json()["book"]["count_ledger_cash"] is False
    assert ok.json()["liquidity"]["now"] == "10000000"
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    amounts = {l["id"]: l["amount"] for l in b["pyramid"]["layers"]}
    assert amounts["cash"] == "15000000" and b["cash_source"] == "book"  # the two accounts only; the ledger's 95 tr left out
    assert Decimal(b["pyramid"]["funding"]["from_cash"]) <= Decimal("15000000")  # never more cash than the book holds
