from datetime import date

from investment_agent.domain.corporate_suggestions import classify, suggestions, yearly_costs
from investment_agent.domain.ledger import parse_events

TODAY = date(2026, 11, 2)


def _ledger(*extra):
    rows = [{"event_id": "d0", "type": "deposit", "effective_at": "2026-01-02", "sequence": 0, "amount": "100000000"},
            {"event_id": "b1", "type": "buy", "effective_at": "2026-01-05", "sequence": 0, "security_id": "FPT", "quantity": 1000,
             "price": "50000", "fee": "75000", "tax": "0"}]
    return parse_events(rows + list(extra))


def _event(kind="dividend_cash", title="Trả cổ tức bằng tiền mặt", exright="2026-06-10", record="2026-06-11", payout="2026-07-01",
           ratio=0.07, vps=700.0, symbol="FPT", id_="FPT-1"):
    return {"id": id_, "symbol": symbol, "kind": kind, "title": f"{title} - x", "key_date": exright, "exright": exright, "record": record,
            "payout": payout, "ratio": ratio, "value_per_share": vps, "code": "DIV"}


def test_issue_titles_are_told_apart():
    assert classify(_event()) == "cash"
    assert classify(_event(kind="issue", title="Trả Cổ tức bằng Cổ phiếu tỉ lệ 10.0%", vps=None)) == "stock"
    assert classify(_event(kind="issue", title="Cổ phiếu thưởng tỉ lệ 20.0%", vps=None)) == "stock"
    assert classify(_event(kind="issue", title="Quyền mua CP cho Cổ đông hiện hữu tỉ lệ 20.0%", vps=None)) == "rights"
    assert classify(_event(kind="issue", title="Phát hành cho CBCNV", vps=None)) is None
    assert classify(_event(vps=None)) is None  # a cash dividend without an amount per share is not drafted


def test_a_cash_dividend_is_drafted_for_shares_held_before_the_ex_date_with_five_percent_tax():
    out = suggestions(_ledger(), [_event()], today=TODAY, dismissed=set())
    s = out[0]
    assert s["status"] == "to_record" and s["kind"] == "cash" and s["eligible"] == 1000
    assert s["draft"] == {"type": "cash_dividend_entitlement", "effective_at": "2026-06-09", "action_id": "FPT-1", "security_id": "FPT",
                          "record_date": "2026-06-11", "payment_date": "2026-07-01", "eligible_quantity": 1000, "expected_gross": "700000",
                          "expected_tax": "35000"}
    bought_on_ex_date = suggestions(_ledger(), [_event(exright="2026-01-05", record="2026-01-06")], today=TODAY, dismissed=set())
    assert bought_on_ex_date == []  # bought on the ex-date: not entitled


def test_after_the_entitlement_the_payment_is_drafted_once_the_pay_date_has_passed():
    entitled = {"event_id": "q1", "type": "cash_dividend_entitlement", "effective_at": "2026-06-10", "sequence": 0, "action_id": "FPT-1",
                "security_id": "FPT", "record_date": "2026-06-11", "payment_date": "2026-07-01", "eligible_quantity": 1000,
                "expected_gross": "700000", "expected_tax": "35000"}
    s = suggestions(_ledger(entitled), [_event()], today=TODAY, dismissed=set())[0]
    assert s["status"] == "to_receive" and s["draft"] == {"type": "cash_dividend_payment", "effective_at": "2026-07-01", "action_id": "FPT-1",
                                                          "received_net": "665000", "tax_withheld": "35000"}
    early = suggestions(_ledger(entitled), [_event()], today=date(2026, 6, 20), dismissed=set())[0]
    assert early["status"] == "waiting" and early["draft"] is None
    paid = {"event_id": "p1", "type": "cash_dividend_payment", "effective_at": "2026-07-01", "sequence": 0, "action_id": "FPT-1",
            "received_net": "665000", "tax_withheld": "35000"}
    assert suggestions(_ledger(entitled, paid), [_event()], today=TODAY, dismissed=set()) == []


def test_a_hand_entry_with_the_same_record_date_counts_as_recorded():
    manual = {"event_id": "q9", "type": "cash_dividend_entitlement", "effective_at": "2026-06-10", "sequence": 0, "action_id": "div-FPT-2026",
              "security_id": "FPT", "record_date": "2026-06-11", "payment_date": None, "eligible_quantity": 1000, "expected_gross": "700000",
              "expected_tax": "35000"}
    paid = {"event_id": "p9", "type": "cash_dividend_payment", "effective_at": "2026-07-01", "sequence": 0, "action_id": "div-FPT-2026",
            "received_net": "665000", "tax_withheld": "35000"}
    assert suggestions(_ledger(manual, paid), [_event()], today=TODAY, dismissed=set()) == []


def test_bonus_shares_round_down_and_wait_for_the_credit():
    ev = _event(kind="issue", title="Trả Cổ tức bằng Cổ phiếu tỉ lệ 15.0%", ratio=0.15, vps=None, id_="FPT-2")
    s = suggestions(_ledger({"event_id": "b2", "type": "buy", "effective_at": "2026-02-02", "sequence": 0, "security_id": "FPT", "quantity": 33,
                             "price": "50000", "fee": "0", "tax": "0"}), [ev], today=TODAY, dismissed=set())[0]
    assert s["kind"] == "stock" and s["draft"] == {"type": "stock_dividend_entitlement", "effective_at": "2026-06-09", "action_id": "FPT-2",
                                                    "security_id": "FPT", "record_date": "2026-06-11", "eligible_quantity": 1033, "shares_entitled": 154}
    entitled = {"event_id": "q2", "type": "stock_dividend_entitlement", "effective_at": "2026-06-10", "sequence": 0, "action_id": "FPT-2",
                "security_id": "FPT", "record_date": "2026-06-11", "eligible_quantity": 1000, "shares_entitled": 150}
    s = suggestions(_ledger(entitled), [ev], today=TODAY, dismissed=set())[0]
    assert s["status"] == "to_credit" and s["draft"] == {"type": "stock_dividend_credit", "effective_at": "", "action_id": "FPT-2",
                                                         "shares_credited": 150, "cash_in_lieu": "0"}


def test_rights_upcoming_dismissed_and_old_events():
    rights = _event(kind="issue", title="Quyền mua CP cho Cổ đông hiện hữu tỉ lệ 20.0%", vps=None, id_="FPT-3")
    upcoming = _event(exright="2026-11-20", record="2026-11-21", payout=None, id_="FPT-4")
    old = _event(exright="2025-08-01", record="2025-08-02", id_="FPT-5")
    out = {s["id"]: s for s in suggestions(_ledger(), [rights, upcoming, old], today=TODAY, dismissed=set())}
    assert out["FPT-3"]["status"] == "rights" and out["FPT-3"]["draft"] is None
    assert out["FPT-4"]["status"] == "upcoming" and out["FPT-4"]["eligible"] == 1000 and out["FPT-4"]["draft"] is None
    assert "FPT-5" not in out  # before the shares were bought (and beyond 400 days)
    assert [s["id"] for s in suggestions(_ledger(), [_event()], today=TODAY, dismissed={"FPT-1"})] == []


def test_yearly_costs_sum_what_the_ledger_records():
    rows = [{"event_id": "s1", "type": "sell", "effective_at": "2026-03-02", "sequence": 0, "security_id": "FPT", "quantity": 100, "price": "60000",
             "fee": "9000", "tax": "6000"},
            {"event_id": "q1", "type": "cash_dividend_entitlement", "effective_at": "2026-06-10", "sequence": 0, "action_id": "FPT-1",
             "security_id": "FPT", "record_date": "2026-06-11", "payment_date": None, "eligible_quantity": 900, "expected_gross": "630000",
             "expected_tax": "31500"},
            {"event_id": "p1", "type": "cash_dividend_payment", "effective_at": "2026-07-01", "sequence": 0, "action_id": "FPT-1",
             "received_net": "598500", "tax_withheld": "31500"}]
    assert yearly_costs(_ledger(*rows)) == [{"year": 2026, "sell_value": "6000000", "fees": "84000", "sell_tax": "6000", "dividends": "630000",
                                             "dividend_tax": "31500", "total": "121500"}]


def test_cash_and_bonus_shares_on_one_record_date_are_matched_by_kind():
    cash, bonus = _event(), _event(kind="issue", title="Cổ phiếu thưởng tỉ lệ 10.0%", ratio=0.1, vps=None, id_="FPT-2")
    cash_line = {"event_id": "q1", "type": "cash_dividend_entitlement", "effective_at": "2026-06-09", "sequence": 0, "action_id": "FPT-1",
                 "security_id": "FPT", "record_date": "2026-06-11", "payment_date": "2026-07-01", "eligible_quantity": 1000,
                 "expected_gross": "700000", "expected_tax": "35000"}
    paid = {"event_id": "p1", "type": "cash_dividend_payment", "effective_at": "2026-07-01", "sequence": 0, "action_id": "FPT-1",
            "received_net": "665000", "tax_withheld": "35000"}
    out = suggestions(_ledger(cash_line, paid), [cash, bonus], today=TODAY, dismissed=set())
    assert [(s["id"], s["status"]) for s in out] == [("FPT-2", "to_record")]


def test_a_hand_entry_near_the_ex_date_counts_even_with_another_record_date():
    manual = {"event_id": "q9", "type": "cash_dividend_entitlement", "effective_at": "2026-06-10", "sequence": 0, "action_id": "div-FPT",
              "security_id": "FPT", "record_date": "2026-06-12", "payment_date": None, "eligible_quantity": 1000, "expected_gross": "700000",
              "expected_tax": "35000"}
    paid = {"event_id": "p9", "type": "cash_dividend_payment", "effective_at": "2026-07-01", "sequence": 0, "action_id": "div-FPT",
            "received_net": "665000", "tax_withheld": "35000"}
    assert suggestions(_ledger(manual, paid), [_event(record=None)], today=TODAY, dismissed=set()) == []


def test_the_entitlement_is_dated_the_day_before_the_ex_date_and_a_missing_record_date_is_left_for_the_owner():
    sold_on_ex_date = {"event_id": "s1", "type": "sell", "effective_at": "2026-06-10", "sequence": 0, "security_id": "FPT", "quantity": 1000,
                       "price": "52000", "fee": "0", "tax": "0"}
    s = suggestions(_ledger(sold_on_ex_date), [_event(record=None)], today=TODAY, dismissed=set())[0]
    assert s["eligible"] == 1000 and s["draft"]["effective_at"] == "2026-06-09" and s["draft"]["record_date"] == ""


def test_bonus_under_one_share_gets_no_draft_and_the_credit_date_is_left_for_the_owner():
    tiny = _event(kind="issue", title="Cổ phiếu thưởng tỉ lệ 0.05%", ratio=0.0005, vps=None, id_="FPT-7")
    s = suggestions(_ledger(), [tiny], today=TODAY, dismissed=set())[0]
    assert s["status"] == "under_one_share" and s["draft"] is None
    entitled = {"event_id": "q2", "type": "stock_dividend_entitlement", "effective_at": "2026-06-09", "sequence": 0, "action_id": "FPT-2",
                "security_id": "FPT", "record_date": "2026-06-11", "eligible_quantity": 1000, "shares_entitled": 150}
    ev = _event(kind="issue", title="Cổ phiếu thưởng tỉ lệ 15.0%", ratio=0.15, vps=None, id_="FPT-2")
    assert suggestions(_ledger(entitled), [ev], today=TODAY, dismissed=set())[0]["draft"]["effective_at"] == ""


def test_pending_bonus_shares_count_toward_entitlement_as_the_ledger_does():
    bonus = {"event_id": "q2", "type": "stock_dividend_entitlement", "effective_at": "2026-03-01", "sequence": 0, "action_id": "B-1",
             "security_id": "FPT", "record_date": "2026-03-02", "eligible_quantity": 1000, "shares_entitled": 100}
    assert suggestions(_ledger(bonus), [_event()], today=TODAY, dismissed=set())[0]["eligible"] == 1100
