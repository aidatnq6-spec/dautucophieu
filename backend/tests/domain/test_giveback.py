from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.giveback import giveback, giveback_alerts, goal_alerts, goal_status
from investment_agent.domain.ledger import parse_events

TODAY = date(2025, 3, 1)


def _days(start, values):
    return [(start + timedelta(days=i), float(v)) for i, v in enumerate(values)]


def _ev(*rows):
    out = [{"event_id": "d0", "type": "deposit", "effective_at": "2024-12-01", "sequence": 0, "amount": "1000000000"}]
    for i, (kind, day, symbol, qty, price) in enumerate(rows, 1):
        out.append({"event_id": f"e{i}", "type": kind, "effective_at": day, "sequence": i, "security_id": symbol, "quantity": qty,
                    "price": price, "fee": "0", "tax": "0"})
    return parse_events(out)


def _row(out, symbol):
    return next(r for r in out["rows"] if r["symbol"] == symbol)


def test_peak_gain_today_and_what_was_given_back_follow_the_adjusted_closes_against_the_adjusted_cost():
    # bought at 52 000 đồng; the adjusted close that day is 50 (thousand đồng): every later close is measured against 50
    closes = {"FPT": _days(date(2025, 1, 1), [50] * 10 + [70] * 5 + [55] * 5)}
    out = giveback(_ev(("buy", "2025-01-01", "FPT", 100, "52000")), closes=closes, today=TODAY)
    r = _row(out, "FPT")
    assert r["since"] == "2025-01-01" and r["reason"] is None
    assert r["peak"] == {"gain": "2080000", "ratio": "0.4000", "on": "2025-01-11"}  # 40% of the real cost of 5 200 000
    assert r["now"] == {"gain": "520000", "ratio": "0.1000", "on": "2025-01-20"}
    assert r["given_back"] == "1560000" and r["share"] == "0.7500" and r["sessions_since_peak"] == 9
    assert r["never_gained"] is False


def test_a_holding_that_never_gained_has_nothing_given_back():
    closes = {"HPG": _days(date(2025, 1, 1), [20, 19, 18, 18])}
    r = _row(giveback(_ev(("buy", "2025-01-01", "HPG", 100, "20000")), closes=closes, today=TODAY), "HPG")
    assert r["never_gained"] is True and r["peak"] is None and r["given_back"] is None and r["share"] is None
    assert r["now"]["ratio"] == "-0.1000"


def test_only_the_current_holding_period_counts_after_selling_out_and_buying_again():
    closes = {"FPT": _days(date(2025, 1, 1), [50, 80, 80, 60, 60, 66])}
    events = _ev(("buy", "2025-01-01", "FPT", 100, "50000"), ("sell", "2025-01-03", "FPT", 100, "80000"), ("buy", "2025-01-05", "FPT", 100, "60000"))
    r = _row(giveback(events, closes=closes, today=TODAY), "FPT")
    assert r["since"] == "2025-01-05" and r["peak"]["on"] == "2025-01-06" and r["peak"]["ratio"] == "0.1000"
    assert r["given_back"] == "0" and r["share"] == "0.0000"


def test_buying_more_averages_the_adjusted_cost_and_the_gain_counts_the_shares_held_that_day():
    closes = {"FPT": _days(date(2025, 1, 1), [50, 60, 40, 50])}
    events = _ev(("buy", "2025-01-01", "FPT", 100, "50000"), ("buy", "2025-01-03", "FPT", 100, "40000"))
    r = _row(giveback(events, closes=closes, today=TODAY), "FPT")
    assert r["peak"] == {"gain": "1000000", "ratio": "0.2000", "on": "2025-01-02"}  # 100 shares, 60 against 50
    assert r["now"] == {"gain": "1000000", "ratio": "0.1111", "on": "2025-01-04"}  # 200 shares, 50 against 45


def test_a_buy_day_without_a_stored_close_is_not_counted_and_says_why():
    closes = {"FPT": _days(date(2025, 1, 5), [50, 60])}
    r = _row(giveback(_ev(("buy", "2025-01-01", "FPT", 100, "50000")), closes=closes, today=TODAY), "FPT")
    assert r["peak"] is None and r["now"] is None and r["reason"] == "Chưa có giá đã lưu tại ngày mua 01/01/2025"
    none = _row(giveback(_ev(("buy", "2025-01-01", "VCB", 100, "50000")), closes={}, today=TODAY), "VCB")
    assert none["reason"] == "Chưa có giá đã lưu của mã"


def test_the_portfolio_adds_each_day_only_when_every_holding_has_a_close_that_day():
    fpt = _days(date(2025, 1, 1), [50, 60, 55, 50])
    hpg = [p for p in _days(date(2025, 1, 1), [20, 22, 24, 20]) if p[0] != date(2025, 1, 3)]
    events = _ev(("buy", "2025-01-01", "FPT", 100, "50000"), ("buy", "2025-01-01", "HPG", 100, "20000"))
    out = giveback(events, closes={"FPT": fpt, "HPG": hpg}, today=TODAY)
    p = out["portfolio"]
    assert p["skipped"] == 1  # 03/01: HPG has no close
    assert p["peak"] == {"gain": "1200000", "ratio": "0.1714", "on": "2025-01-02"}  # 1 000 000 + 200 000 on 7 000 000
    assert p["now"]["gain"] == "0" and p["given_back"] == "1200000" and p["share"] == "1.0000"
    assert [d["on"] for d in p["days"]] == ["2025-01-01", "2025-01-02", "2025-01-04"]
    assert p["days"][1] == {"on": "2025-01-02", "gain": "1200000", "value": "8200000"}


def test_a_closed_position_is_left_out():
    closes = {"FPT": _days(date(2025, 1, 1), [50, 60])}
    out = giveback(_ev(("buy", "2025-01-01", "FPT", 100, "50000"), ("sell", "2025-01-02", "FPT", 100, "60000")), closes=closes, today=TODAY)
    assert out["rows"] == [] and out["portfolio"]["peak"] is None


def test_reminders_need_both_thresholds_and_come_once_per_holding_period_until_the_share_falls_back():
    rows = [{"symbol": "FPT", "since": "2025-01-01", "peak": {"gain": "2000000", "ratio": "0.4000", "on": "2025-01-11"},
             "now": {"gain": "500000", "ratio": "0.1000", "on": "2025-01-20"}, "given_back": "1500000", "share": "0.7500"},
            {"symbol": "HPG", "since": "2025-01-01", "peak": {"gain": "100000", "ratio": "0.0500", "on": "2025-01-02"},
             "now": {"gain": "0", "ratio": "0.0000", "on": "2025-01-20"}, "given_back": "100000", "share": "1.0000"}]
    assert giveback_alerts(rows, min_gain=None, share=None, alerted=set()) == ([], set())
    alerts, alerted = giveback_alerts(rows, min_gain=Decimal("0.3"), share=Decimal("0.5"), alerted=set())
    assert [a["symbol"] for a in alerts] == ["FPT"] and alerted == {"FPT@2025-01-01"}  # HPG never gained 30%
    assert giveback_alerts(rows, min_gain=Decimal("0.3"), share=Decimal("0.5"), alerted=alerted)[0] == []
    back = [{**rows[0], "share": "0.2000"}]
    assert giveback_alerts(back, min_gain=Decimal("0.3"), share=Decimal("0.5"), alerted=alerted) == ([], set())


DAYS = [{"on": "2025-01-01", "gain": "0", "value": "100"}, {"on": "2025-01-02", "gain": "30", "value": "130"},
        {"on": "2025-01-03", "gain": "60", "value": "160"}, {"on": "2025-01-04", "gain": "10", "value": "110"}]


def test_a_goal_says_whether_it_is_enough_today_and_since_when():
    goal = {"id": "g1", "name": "Mua nhà", "amount": "120", "basis": "value", "created_on": "2025-01-02", "closed": None}
    s = goal_status(goal, DAYS[:3])
    assert s["enough"] is True and s["short"] is None and s["since"] == "2025-01-02" and s["days"] == 1 and s["before_goal"] is False
    s = goal_status(goal, DAYS)
    assert s["enough"] is False and s["short"] == "10" and s["since"] is None
    assert s["last"] == {"from": "2025-01-02", "to": "2025-01-03", "excess": "40"}
    by_gain = goal_status({**goal, "amount": "50", "basis": "gain", "created_on": "2025-01-04"}, DAYS)
    assert by_gain["last"] == {"from": "2025-01-03", "to": "2025-01-03", "excess": "10"} and by_gain["last_before_goal"] is True
    assert goal_status(goal, [])["enough"] is None


def test_goal_reminders_come_when_a_goal_becomes_enough_and_when_it_falls_short_again():
    open_goal = {"id": "g1", "name": "Mua nhà", "amount": "120", "closed": None}
    enough = {"enough": True, "short": None, "since": "2025-01-02"}
    short = {"enough": False, "short": "10", "since": None}
    alerts, states = goal_alerts([(open_goal, short)], states={})
    assert alerts == [] and states == {"g1": "short"}  # first seen short: nothing to say
    alerts, states = goal_alerts([(open_goal, enough)], states=states)
    assert [a["kind"] for a in alerts] == ["enough"] and states == {"g1": "enough"}
    assert goal_alerts([(open_goal, enough)], states=states)[0] == []
    alerts, states = goal_alerts([(open_goal, short)], states=states)
    assert [a["kind"] for a in alerts] == ["short_again"] and states == {"g1": "short"}
    closed = {**open_goal, "closed": {"kind": "done", "on": "2025-01-05"}}
    assert goal_alerts([(closed, enough)], states=states) == ([], {})
    assert goal_alerts([(open_goal, {"enough": None})], states=states) == ([], states)  # no figures: keep what was known
