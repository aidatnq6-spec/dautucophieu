from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client
from test_overview_route import MARKET, PROFILE, buy_fpt, setup_owner  # risk answers "C" → balanced (35%); FPT bought 100 × 50,000


def client(profile=None):
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()), market=MARKET)
    setup_owner(c, clock)
    if profile is not None:
        preview = call(c, clock, "POST", "/internal/profile/assessment", {"profile": profile, "ledger_value": None}).json()
        call(c, clock, "PUT", "/internal/profile", {"profile": profile, "ledger_value": None, "reviewed_net": preview["net"], "expected_version": 1,
                                                     "request_id": "p2"})
    buy_fpt(c, clock)
    return c, clock


def save(c, clock, total, version=0, rid="eb1"):
    return call(c, clock, "PUT", "/internal/equity-budget", {"total": total, "expected_version": version, "request_id": rid})


def test_without_a_total_the_page_asks_for_one():
    c, clock = client()
    assert call(c, clock, "GET", "/internal/equity-budget").json() == {"version": 0, "budget": {"status": "no_total"}}


def test_budget_follows_the_risk_group_and_counts_holdings_at_cost():
    c, clock = client()
    assert save(c, clock, "2000000000").status_code == 200
    body = call(c, clock, "GET", "/internal/equity-budget").json()
    b = body["budget"]
    assert body["version"] == 1 and b["group"] == "balanced" and b["ratio"] == "0.35"
    assert b["budget"] == "700000000" and b["held_cost"] == "5000000" and b["room"] == "695000000"


def test_emergency_reserve_is_taken_out_before_the_ratio():
    c, clock = client({**PROFILE, "emergency_reserve": "100000000",
                       "assets": [{"asset_id": "cash", "kind": "deposit", "amount": "1000000000", "liquidity": "liquid", "earmarks": [{"purpose": "emergency", "amount": "100000000"}]}]})
    save(c, clock, "2000000000")
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert b["deductions"] == "100000000" and b["budget"] == "665000000"


def test_concentration_is_measured_on_the_stock_budget_once_set():
    c, clock = client()
    before = call(c, clock, "GET", "/internal/concentration").json()
    assert before["basis"] == "investable_capital" and before["capital"] == "1000000000"
    save(c, clock, "100000000")  # 35% → 35,000,000 for stocks
    after = call(c, clock, "GET", "/internal/concentration").json()
    assert after["basis"] == "equity_budget" and after["capital"] == "35000000" and after["tickers"][0]["weight"] == "0.1429"  # cost 5 triệu


def test_invalid_totals_are_refused():
    c, clock = client()
    assert save(c, clock, "-5").status_code == 422
    assert save(c, clock, "abc").status_code == 422


def test_a_reserve_entered_by_hand_replaces_the_profile_deduction():
    c, clock = client({**PROFILE, "emergency_reserve": "100000000",
                       "assets": [{"asset_id": "cash", "kind": "deposit", "amount": "1000000000", "liquidity": "liquid", "earmarks": [{"purpose": "emergency", "amount": "100000000"}]}]})
    ok = call(c, clock, "PUT", "/internal/equity-budget", {"total": "2000000000", "reserve": "300000000", "expected_version": 0, "request_id": "eb1"})
    assert ok.status_code == 200
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert b["deductions"] == "300000000" and b["deductions_source"] == "manual" and b["budget"] == "595000000"  # (2 tỷ − 300 tr) × 35%
    assert b["profile_deductions"] == "100000000"
    call(c, clock, "PUT", "/internal/equity-budget", {"total": "2000000000", "reserve": None, "expected_version": 1, "request_id": "eb2"})
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert b["deductions"] == "100000000" and b["deductions_source"] == "profile"


def test_a_negative_reserve_is_refused():
    c, clock = client()
    assert call(c, clock, "PUT", "/internal/equity-budget", {"total": "2000000000", "reserve": "-1", "expected_version": 0, "request_id": "eb1"}).status_code == 422


def test_layers_add_up_to_the_total_with_stocks_and_cash_from_the_ledger_and_build_the_pyramid():
    c, clock = client()  # Cân bằng 35%; ledger: 100 tr deposited, FPT bought for 5 tr → 95 tr cash, 5 tr stocks at cost
    ok = call(c, clock, "PUT", "/internal/equity-budget", {"layers": {"deposit": "300000000", "bond": "0", "gold": "100000000", "crypto": "0"},
                                                          "reserve": "100000000", "expected_version": 0, "request_id": "eb1"})
    assert ok.status_code == 200
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert b["total"] == "600000000"  # 100 reserve + 300 deposits + 95 ledger cash + 100 gold + 5 stocks at cost
    p = b["pyramid"]
    amounts = {l["id"]: l["amount"] for l in p["layers"]}
    assert amounts == {"reserve": "100000000", "cash": "95000000", "deposit": "300000000", "bond": "0", "gold": "100000000", "stocks": "5000000",
                       "crypto": "0"}
    assert b["layers"] == {"deposit": "300000000", "bond": "0", "gold": "100000000", "crypto": "0"}


def test_a_single_total_still_works_without_a_pyramid():
    c, clock = client()
    save(c, clock, "2000000000")
    b = call(c, clock, "GET", "/internal/equity-budget").json()["budget"]
    assert b["total"] == "2000000000" and b["pyramid"] is None


def test_negative_layers_are_refused():
    c, clock = client()
    bad = call(c, clock, "PUT", "/internal/equity-budget", {"layers": {"deposit": "-1", "bond": "0", "gold": "0", "crypto": "0"},
                                                           "expected_version": 0, "request_id": "eb1"})
    assert bad.status_code == 422
