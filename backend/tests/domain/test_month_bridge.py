from datetime import date

from investment_agent.domain.ledger import parse_events
from investment_agent.domain.month_bridge import month_bridge

EVENTS = parse_events([
    {"event_id": "d1", "type": "deposit", "effective_at": "2026-09-01", "sequence": 0, "amount": "100000000"},
    {"event_id": "b1", "type": "buy", "effective_at": "2026-09-02", "sequence": 0, "security_id": "FPT", "quantity": 1000, "price": "50000",
     "fee": "75000", "tax": "0"},
    {"event_id": "d2", "type": "deposit", "effective_at": "2026-10-05", "sequence": 0, "amount": "20000000"},
    {"event_id": "b2", "type": "buy", "effective_at": "2026-10-06", "sequence": 0, "security_id": "HPG", "quantity": 500, "price": "20000",
     "fee": "15000", "tax": "0"},
    {"event_id": "e1", "type": "cash_dividend_entitlement", "effective_at": "2026-10-10", "sequence": 0, "action_id": "a1", "security_id": "FPT",
     "record_date": "2026-10-11", "payment_date": "2026-10-20", "eligible_quantity": 1000, "expected_gross": "1000000", "expected_tax": "50000"},
    {"event_id": "p1", "type": "cash_dividend_payment", "effective_at": "2026-10-20", "sequence": 0, "action_id": "a1", "received_net": "950000",
     "tax_withheld": "50000"},
    {"event_id": "s1", "type": "sell", "effective_at": "2026-10-25", "sequence": 0, "security_id": "FPT", "quantity": 200, "price": "56000",
     "fee": "16800", "tax": "11200"},
    {"event_id": "w1", "type": "withdrawal", "effective_at": "2026-10-28", "sequence": 0, "amount": "5000000"},
])
CLOSES = {"FPT": {date(2026, 9, 30): 52.0, date(2026, 10, 31): 55.0}, "HPG": {date(2026, 10, 31): 21.0}}  # thousand đồng
DAYS = [date(2026, 9, 30), date(2026, 10, 31)]


def test_the_month_s_change_is_split_into_money_in_and_out_each_ticker_dividends_and_costs_with_nothing_left_over():
    out = month_bridge(EVENTS, closes=CLOSES, sessions=DAYS, month="2026-10")
    assert out["status"] == "ok" and out["start_day"] == "2026-09-30" and out["end_day"] == "2026-10-31"
    # start: cash 100,000,000 − 50,075,000 = 49,925,000 + FPT 1,000 × 52,000
    assert out["start"] == "101925000"
    steps = {s["id"]: s["amount"] for s in out["steps"]}
    assert steps == {"flows": "15000000", "ticker:FPT": "3200000", "ticker:HPG": "500000", "dividends": "950000", "costs": "-43000"}
    # FPT: 800 × 55,000 − 1,000 × 52,000 + 200 × 56,000 = 3,200,000; HPG: 500 × 21,000 − 500 × 20,000
    assert out["end"] == str(101925000 + 15000000 + 3200000 + 500000 + 950000 - 43000) and out["other"] == "0"


def test_a_ticker_without_a_close_on_either_day_stops_the_bridge_and_is_named():
    out = month_bridge(EVENTS, closes={"FPT": CLOSES["FPT"]}, sessions=DAYS, month="2026-10")
    assert out == {"status": "missing_prices", "month": "2026-10", "missing": ["HPG"], "start_day": "2026-09-30", "end_day": "2026-10-31"}


def test_the_first_month_starts_from_nothing():
    out = month_bridge(EVENTS, closes=CLOSES, sessions=DAYS, month="2026-09")
    assert out["start"] == "0" and out["start_day"] is None and out["end_day"] == "2026-09-30"
    steps = {s["id"]: s["amount"] for s in out["steps"]}
    assert steps == {"flows": "100000000", "ticker:FPT": "2000000", "costs": "-75000"} and out["other"] == "0"


def test_a_month_without_sessions_says_so():
    assert month_bridge(EVENTS, closes=CLOSES, sessions=DAYS, month="2026-12")["status"] == "no_sessions"
