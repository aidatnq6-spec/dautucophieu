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


def save_book(c, clock, deposits=DEPOSITS, accounts=ACCOUNTS, version=0, rid="db1", **more):
    return call(c, clock, "PUT", "/internal/deposit-book", {"deposits": deposits, "accounts": accounts, "expected_version": version, "request_id": rid,
                                                           **more})


def save_layers(c, clock, version=0):
    return call(c, clock, "PUT", "/internal/equity-budget", {"layers": {"deposit": "300000000", "bond": "0", "gold": "100000000", "crypto": "0"},
                                                            "reserve": "120000000", "expected_version": version, "request_id": "eb1"})


def test_an_empty_book_has_no_rows_and_liquidity_from_the_ledger_cash(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/deposit-book").json()
    assert body["version"] == 0 and body["book"] == {"accounts": [], "deposits": [], "bonds": [], "gold": [], "crypto": [], "count_ledger_cash": True,
                                                     "reserve": None}
    assert body["liquidity"]["now"] == "95000000" and body["calendar"]["months"] == []


def test_saved_book_gives_the_calendar_and_liquidity_against_the_reserve_of_the_pyramid(tmp_path):
    c, clock = client(tmp_path)
    ok = save_book(c, clock, reserve="120000000")
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
    assert amounts["gold"] == "0" and amounts["reserve"] == "0"  # the hand-entered gold and reserve no longer count once there is a book
    assert b["deposit_source"] == "book" and b["total"] == "415000000"  # 110 + 300 + 5 stocks


def test_the_book_alone_builds_the_pyramid_with_every_layer_from_its_lists(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/equity-budget").json()["budget"] == {"status": "no_total"}
    save_book(c, clock, deposits=[])
    body = call(c, clock, "GET", "/internal/equity-budget").json()
    amounts = {l["id"]: l["amount"] for l in body["budget"]["pyramid"]["layers"]}
    assert body["budget"]["status"] == "ok" and body["budget"]["layer_sources"] == dict.fromkeys(("deposit", "bond", "gold", "crypto"), "book")
    assert amounts == {"reserve": "0", "cash": "110000000", "deposit": "0", "bond": "0", "gold": "0", "stocks": "5000000", "crypto": "0"}


def test_the_reserve_is_entered_in_the_book_and_blank_uses_the_profile(tmp_path):
    c, clock = client(tmp_path)
    save_layers(c, clock)  # the old hand-entered reserve, 120 tr, no longer counts once there is a book
    ok = call(c, clock, "PUT", "/internal/deposit-book", {"deposits": [], "accounts": ACCOUNTS, "reserve": "50000000",
                                                         "expected_version": 0, "request_id": "db1"})
    assert ok.json()["book"]["reserve"] == "50000000" and ok.json()["liquidity"]["reserve"] == "50000000"
    assert ok.json()["profile_reserve"] == "0"  # the figure a blank reserve falls back to
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert b["deductions"] == "50000000" and b["deductions_source"] == "manual" and b["reserve"] == "50000000"
    save_book(c, clock, deposits=[], version=1, rid="db2")  # reserve left out = blank
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert b["deductions"] == "0" and b["deductions_source"] == "profile"
    assert save_book(c, clock, deposits=[], version=2, rid="db3").status_code == 200
    bad = call(c, clock, "PUT", "/internal/deposit-book", {"deposits": [], "accounts": [], "reserve": "-1", "expected_version": 3, "request_id": "db4"})
    assert bad.status_code == 422


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


def test_bond_gold_and_crypto_lists_replace_their_hand_entered_layers_and_bond_income_uses_each_rate(tmp_path):
    c, clock = client(tmp_path)
    save_layers(c, clock)  # by hand: bond 0, gold 100 tr, crypto 0
    ok = call(c, clock, "PUT", "/internal/deposit-book", {"deposits": [], "accounts": [], "expected_version": 0, "request_id": "db1",
                                                         "bonds": [{"id": "a", "name": "Quỹ A", "amount": "120000000", "rate": "8"},
                                                                   {"id": "b", "name": "Quỹ B", "amount": "60000000", "rate": None}],
                                                         "gold": [{"id": "g", "name": "Vàng nhẫn", "amount": "40000000"}]})
    assert ok.status_code == 200 and len(ok.json()["book"]["bonds"]) == 2
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    amounts = {l["id"]: l["amount"] for l in b["pyramid"]["layers"]}
    assert amounts["bond"] == "180000000" and amounts["gold"] == "40000000" and amounts["crypto"] == "0"
    assert b["layer_sources"] == {"deposit": "book", "bond": "book", "gold": "book", "crypto": "book"}
    income = call(c, clock, "GET", "/internal/passive-income").json()["income"]
    assert income["bond"] == "1150000" and income["bond_default_rate_count"] == 1  # 120 tr × 8% / 12 + 60 tr × 7% (default) / 12


def test_a_fund_row_is_valued_at_units_times_the_stored_nav_in_the_book_the_pyramid_and_passive_income(tmp_path):
    from investment_agent.market.fund_nav import FundNavStore
    FundNavStore(tmp_path).save({"source": "Fmarket", "funds": {"VFF": {"name": "Quỹ A", "nav": "20000", "date": "2027-01-14"}}})
    c, clock = client(tmp_path)
    ok = call(c, clock, "PUT", "/internal/deposit-book", {"deposits": [], "accounts": [], "expected_version": 0, "request_id": "db1",
                                                         "bonds": [{"id": "a", "name": "Quỹ A", "amount": "50000000", "rate": "8", "fund": "VFF", "units": "3000"},
                                                                   {"id": "b", "name": "Quỹ B", "amount": "10000000", "rate": None, "fund": "ZZZ", "units": "5"}]})
    assert ok.status_code == 200
    rows = ok.json()["bond_values"]
    assert rows[0] == {"id": "a", "cost": "50000000", "value": "60000000", "source": "nav", "fund": "VFF", "nav": "20000", "nav_date": "2027-01-14",
                       "stale": False, "change": "10000000"}
    assert rows[1]["source"] == "no_nav" and rows[1]["value"] == "10000000"
    assert ok.json()["nav_source"] == "Fmarket"
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert {l["id"]: l["amount"] for l in b["pyramid"]["layers"]}["bond"] == "70000000"
    income = call(c, clock, "GET", "/internal/passive-income").json()["income"]
    assert income["bond"] == "458333"  # 60 tr × 8% / 12 + 10 tr × 7% (default) / 12
    bad = call(c, clock, "PUT", "/internal/deposit-book", {"deposits": [], "accounts": [], "expected_version": 1, "request_id": "db2",
                                                          "bonds": [{"id": "a", "name": "Quỹ A", "amount": "1", "rate": None, "fund": "VFF"}]})
    assert bad.status_code == 422


def test_a_gold_row_is_valued_at_chi_times_the_buying_price_in_the_book_and_the_pyramid(tmp_path):
    from investment_agent.market.gold_price import GoldPriceStore
    ring = "Nhẫn tròn Phú Quý 999.9"
    GoldPriceStore(tmp_path).save({"source": "Phú Quý", "unit": "chỉ", "as_of": "2027-01-15T08:30:00+07:00",
                                   "kinds": {ring: {"buy": "13650000", "sell": "14050000"}, "Vàng trang sức 99": {"buy": "1", "sell": None}}})
    c, clock = client(tmp_path)
    ok = call(c, clock, "PUT", "/internal/deposit-book", {"deposits": [], "accounts": [], "expected_version": 0, "request_id": "db1",
                                                         "gold": [{"id": "g", "name": "Vàng nhẫn", "amount": "39364000", "kind": ring, "chi": "3"}]})
    assert ok.status_code == 200
    body = ok.json()
    assert body["gold_values"][0]["value"] == "40950000" and body["gold_values"][0]["source"] == "price"
    assert body["gold_kinds"] == [ring, "Vàng trang sức 99"] and body["gold_source"] == "Phú Quý"
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert {l["id"]: l["amount"] for l in b["pyramid"]["layers"]}["gold"] == "40950000"
    bad = call(c, clock, "PUT", "/internal/deposit-book", {"deposits": [], "accounts": [], "expected_version": 1, "request_id": "db2",
                                                          "gold": [{"id": "g", "name": "Vàng", "amount": "1", "kind": ring}]})
    assert bad.status_code == 422
