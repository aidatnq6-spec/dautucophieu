from datetime import date

from investment_agent.domain.ledger import parse_events
from investment_agent.domain.ledger_import import MESSAGES, plan_import

DEP = {"event_id": "d1", "type": "deposit", "effective_at": "2026-01-02", "sequence": 0, "amount": "100000000"}


def order(no, symbol="AAA", kind="buy", day="2026-03-02", qty=100, price="20000", fee="300", tax="0", line=1):
    return {"line": line, "symbol": symbol, "type": kind, "date": date.fromisoformat(day), "quantity": qty, "price": price, "fee": fee, "tax": tax, "order_no": no}


def events(*extra):
    return parse_events([DEP, *extra])


def test_new_orders_become_trades_in_date_order_with_free_sequence_numbers_and_sales_first_within_a_day():
    plan = plan_import(events(), events(), [order("2", kind="sell", day="2026-03-05", qty=50), order("3", day="2026-03-05", qty=10), order("1")])
    assert plan["blocked"] is None and plan["counts"] == {"new": 3, "already": 0, "manual": 0, "before_opening": 0}
    made = plan["events"]
    assert [e["event_id"] for e in made] == ["tcbs-1", "tcbs-2", "tcbs-3"]
    assert [(e["effective_at"], e["sequence"], e["type"]) for e in made] == [("2026-03-02", 0, "buy"), ("2026-03-05", 0, "sell"), ("2026-03-05", 1, "buy")]
    assert made[0]["fee"] == "300" and made[0]["security_id"] == "AAA"


def test_orders_already_imported_even_if_since_cancelled_are_not_added_again():
    first = plan_import(events(), events(), [order("1")])["events"]
    ledger = events(*first)
    plan = plan_import(ledger, events(), [order("1"), order("2", day="2026-03-03")])
    assert plan["counts"]["already"] == 1 and plan["counts"]["new"] == 1 and [r["status"] for r in plan["rows"]] == ["already", "new"]


def test_a_trade_typed_by_hand_with_the_same_day_ticker_side_quantity_and_price_is_not_doubled():
    typed = {"event_id": "b1", "type": "buy", "effective_at": "2026-03-02", "sequence": 0, "security_id": "AAA", "quantity": 100, "price": "20000", "fee": "0", "tax": "0"}
    plan = plan_import(events(typed), events(typed), [order("1"), order("2")])
    assert [r["status"] for r in plan["rows"]] == ["manual", "new"]  # one typed trade answers for one order only
    assert plan["events"][0]["sequence"] == 1


def test_orders_before_the_opening_balance_stay_out_and_are_counted():
    opening = {"event_id": "o1", "type": "opening_balance", "effective_at": "2026-02-01", "sequence": 0, "cash": "50000000", "positions": []}
    ledger = parse_events([opening])
    plan = plan_import(ledger, ledger, [order("1", day="2026-01-15"), order("2")])
    assert [r["status"] for r in plan["rows"]] == ["before_opening", "new"] and plan["blocked"] is None


def test_a_set_of_orders_the_ledger_cannot_hold_is_blocked_whole_and_says_which_and_why():
    plan = plan_import(events(), events(), [order("1", qty=10), order("2", symbol="BBB", kind="sell", day="2026-03-04", qty=5)])
    assert plan["blocked"]["code"] == "oversell" and plan["blocked"]["symbol"] == "BBB" and plan["blocked"]["date"] == "2026-03-04"
    assert plan["blocked"]["message"] == MESSAGES["oversell"]
    poor = plan_import(parse_events([]), parse_events([]), [order("1")])
    assert poor["blocked"]["code"] == "cash_negative"
