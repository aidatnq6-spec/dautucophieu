from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from investment_agent.domain.thesis import (ThesisError, advance, edit_thesis, evaluate, hold_condition, mark_sent, new_thesis, scenario, similar,
                                            validate_thesis)

D = Decimal


def cond(kind, set_on="2026-10-01", **params):
    return {"id": "c1", "kind": kind, "params": params, "set_on": set_on}


def test_loss_against_cost_breaks_at_the_owners_percentage():
    c = cond("loss_vs_cost", pct="10")
    assert evaluate(c, {"price": D("45000"), "cost": D("50000")})["state"] == "broken"
    assert evaluate(c, {"price": D("45100"), "cost": D("50000")})["state"] == "ok"
    out = evaluate(c, {"price": D("40000"), "cost": D("50000")})
    assert out["reading"] == "giá 40,00 so với giá vốn 50,00 (−20,0%)"
    missing = evaluate(c, {"price": None, "cost": D("50000")})
    assert missing["state"] == "unknown" and missing["reason"] == "Chưa có giá khớp"


def test_close_below_reads_the_level_in_thousand_dong():
    c = cond("close_below", level="48.5")
    assert evaluate(c, {"close": D("48400")})["state"] == "broken"
    assert evaluate(c, {"close": D("48500")})["state"] == "ok"
    assert evaluate(c, {})["state"] == "unknown"


def test_valuation_conditions_use_the_fair_price_now_and_when_set():
    above = cond("above_fair", pct="20")
    assert evaluate(above, {"price": D("60000"), "fair": D("50000")})["state"] == "broken"
    assert evaluate(above, {"price": D("59000"), "fair": D("50000")})["state"] == "ok"
    assert evaluate(above, {"price": D("60000"), "fair": None})["reason"] == "Chưa có mức hợp lý (định giá tham khảo)"
    cut = {**cond("fair_cut", pct="15"), "fair_at_set": "60000"}
    assert evaluate(cut, {"fair": D("50000")})["state"] == "broken"
    assert evaluate(cut, {"fair": D("52000")})["state"] == "ok"
    assert evaluate(cond("fair_cut", pct="15"), {"fair": D("50000")})["state"] == "unknown"  # no fair price when it was set


def test_quality_conditions():
    f = cond("f_score", n=3)
    assert evaluate(f, {"quality": {"kind": "f_score", "score": 2, "year": "2025"}})["state"] == "broken"
    assert evaluate(f, {"quality": {"kind": "f_score", "score": 4, "year": "2025"}})["state"] == "ok"
    assert evaluate(f, {"quality": None, "quality_reason": "Chưa có số liệu báo cáo chi tiết"})["reason"] == "Chưa có số liệu báo cáo chi tiết"
    h = cond("health_weak")
    assert evaluate(h, {"quality": {"kind": "health", "score": 1, "level": "weak", "year": "Q3/2026"}})["state"] == "broken"
    assert evaluate(h, {"quality": {"kind": "health", "score": 4, "level": "medium", "year": "Q3/2026"}})["state"] == "ok"
    assert evaluate(h, {"quality": {"kind": "health", "score": 4, "level": None, "year": "Q3/2026"}})["state"] == "unknown"


def test_profit_drop_needs_n_latest_quarters_each_below_the_same_quarter_a_year_before():
    c = cond("profit_drop", n=2)
    q = {"2025-Q2": D("100"), "2025-Q3": D("120"), "2026-Q2": D("90"), "2026-Q3": D("110")}
    assert evaluate(c, {"quarters": q})["state"] == "broken"
    assert evaluate(c, {"quarters": {**q, "2026-Q2": D("101")}})["state"] == "ok"
    assert evaluate(c, {"quarters": {"2026-Q2": D("90"), "2026-Q3": D("110")}})["state"] == "unknown"  # no year-earlier quarters


def _daily(values, start=date(2025, 1, 6)):
    return [(start + timedelta(days=i), v) for i, v in enumerate(values)]


def test_weekly_macd_breaks_on_a_cross_down_after_the_condition_was_set():
    rising = [10 + (i / 40) ** 2 for i in range(400)]  # speeding up: MACD clearly above its signal
    falling = rising + [rising[-1] - i * 1.5 for i in range(1, 60)]
    set_on = _daily(falling)[400][0].isoformat()
    c = cond("macd_weekly", set_on=set_on)
    assert evaluate(c, {"daily": _daily(rising)})["state"] == "ok"
    assert evaluate(c, {"daily": _daily(falling)})["state"] == "broken"
    long_before = cond("macd_weekly", set_on=_daily(falling)[-1][0].isoformat())
    assert evaluate(long_before, {"daily": _daily(falling)})["state"] == "ok"  # already below when set: no new cross yet
    assert evaluate(c, {"daily": _daily(rising[:50])})["state"] == "unknown"


def test_chain_and_insider_conditions():
    c = cond("chain_headwind")
    assert evaluate(c, {"chains": ["neutral", "headwind"]})["state"] == "broken"
    assert evaluate(c, {"chains": ["tailwind"]})["state"] == "ok"
    assert evaluate(c, {"chains": []})["reason"] == "Mã không thuộc chuỗi giá trị nào"
    assert evaluate(c, {"chains": [None, "insufficient"]})["state"] == "unknown"
    i = cond("insider_sell")
    sale = {"date": "2026-10-20", "name": "Ông A", "kind": "sell", "volume": 100000}
    assert evaluate(i, {"insider_sells": [sale]})["state"] == "broken"
    assert evaluate(i, {"insider_sells": []})["state"] == "ok"
    assert evaluate(i, {"insider_sells": None})["state"] == "unknown"


def test_a_thesis_needs_reasons_valid_conditions_and_a_loss_limit_when_bought_out_of_fear_of_missing_out():
    ok = validate_thesis({"reasons": ["cheap", "earnings"], "note": "Rẻ, lãi tăng", "conditions": [
        {"kind": "f_score", "params": {"n": 3}}, {"kind": "loss_vs_cost", "params": {"pct": "10"}}]}, company="other")
    assert [c["kind"] for c in ok["conditions"]] == ["f_score", "loss_vs_cost"] and ok["conditions"][0]["id"] != ok["conditions"][1]["id"]
    for raw, company, code in (
            ({"reasons": [], "note": "", "conditions": [{"kind": "loss_vs_cost", "params": {"pct": "10"}}]}, "other", "reason_required"),
            ({"reasons": ["fomo"], "note": "", "conditions": [{"kind": "f_score", "params": {"n": 3}}]}, "other", "loss_limit_required"),
            ({"reasons": ["cheap"], "note": "", "conditions": []}, "other", "condition_required"),
            ({"reasons": ["cheap"], "note": "", "conditions": [{"kind": "f_score", "params": {"n": 3}}]}, "financial", "not_applicable"),
            ({"reasons": ["cheap"], "note": "", "conditions": [{"kind": "health_weak", "params": {}}]}, "other", "not_applicable"),
            ({"reasons": ["cheap"], "note": "", "conditions": [{"kind": "loss_vs_cost", "params": {"pct": "0"}}]}, "other", "invalid_condition"),
            ({"reasons": ["cheap"], "note": "", "conditions": [{"kind": "close_below", "params": {"level": "-1"}}]}, "other", "invalid_condition"),
            ({"reasons": ["cheap"], "note": "", "conditions": [{"kind": "profit_drop", "params": {"n": 9}}]}, "other", "invalid_condition"),
            ({"reasons": ["luck"], "note": "", "conditions": [{"kind": "insider_sell", "params": {}}]}, "other", "invalid_reason"),
            ({"reasons": ["cheap"], "note": "", "conditions": [{"kind": "moon", "params": {}}]}, "other", "invalid_condition")):
        with pytest.raises(ThesisError) as err:
            validate_thesis(raw, company=company)
        assert err.value.code == code


TODAY = date(2026, 11, 2)
BROKEN = {"state": "broken", "reading": "x", "reason": None}


def _thesis(*conds, fair=None):
    raw = {"reasons": ["cheap"], "note": "Rẻ", "conditions": [{"kind": k, "params": p} for k, p in conds]}
    return new_thesis("FPT", validate_thesis(raw, company="other"), today=TODAY, snapshot={"price": "50000", "fair": fair})


def _ids(t):
    return [c["id"] for c in t["conditions"]]


def test_a_broken_condition_stays_broken_when_the_price_recovers_and_is_reported_once():
    t = _thesis(("loss_vs_cost", {"pct": "10"}))
    cid = _ids(t)[0]
    t, events = advance(t, {cid: {"state": "broken", "reading": "giá 44", "reason": None}}, today=TODAY, price=D("44000"))
    c = t["conditions"][0]
    assert c["status"] == "broken" and c["broken_on"] == "2026-11-02" and c["broken_price"] == "44000"
    assert [e["type"] for e in events] == ["first"]
    t, events = advance(t, {cid: {"state": "broken", "reading": "giá 44", "reason": None}}, today=TODAY, price=D("44000"))
    assert [e["type"] for e in events] == ["first"]  # not sent yet: offered again
    t = mark_sent(t, events)
    t, events = advance(t, {cid: {"state": "ok", "reading": "giá 49", "reason": None}}, today=TODAY + timedelta(days=3), price=D("49000"))
    assert events == [] and t["conditions"][0]["status"] == "broken" and t["conditions"][0]["current"] == "giá 49"


def test_each_further_five_percent_fall_since_the_first_report_is_reported_once():
    t = _thesis(("loss_vs_cost", {"pct": "10"}))
    cid = _ids(t)[0]
    t, ev = advance(t, {cid: BROKEN}, today=TODAY, price=D("40000"))
    t = mark_sent(t, ev)
    t, ev = advance(t, {cid: BROKEN}, today=TODAY, price=D("37900"))  # −5.25%
    assert [(e["type"], e["level"]) for e in ev] == [("step", 1)]
    t = mark_sent(t, ev)
    t, ev = advance(t, {cid: BROKEN}, today=TODAY, price=D("37800"))
    assert ev == []
    t, ev = advance(t, {cid: BROKEN}, today=TODAY, price=D("33000"))  # −17.5%
    assert [(e["type"], e["level"]) for e in ev] == [("step", 3)]


def test_unknown_keeps_the_last_known_state_and_says_why():
    t = _thesis(("f_score", {"n": 3}))
    cid = _ids(t)[0]
    t, ev = advance(t, {cid: {"state": "unknown", "reading": None, "reason": "Chưa có F-Score"}}, today=TODAY, price=None)
    assert ev == [] and t["conditions"][0]["status"] == "unknown" and t["conditions"][0]["reason"] == "Chưa có F-Score"


def test_holding_on_with_a_reason_silences_only_that_condition_until_the_review_date():
    t = _thesis(("loss_vs_cost", {"pct": "10"}), ("f_score", {"n": 3}))
    loss, fs = _ids(t)
    t, ev = advance(t, {loss: BROKEN}, today=TODAY, price=D("40000"))
    t = mark_sent(t, ev)
    in30 = TODAY + timedelta(days=30)
    for kwargs, code in (({"cond_id": loss, "reason": "", "until": in30}, "reason_required"),
                         ({"cond_id": loss, "reason": "Chờ KQKD quý 4", "until": None}, "hold_needs_condition_or_date"),
                         ({"cond_id": loss, "reason": "Chờ", "until": TODAY + timedelta(days=91)}, "invalid_review_date"),
                         ({"cond_id": fs, "reason": "Chờ", "until": in30}, "not_broken")):
        with pytest.raises(ThesisError) as err:
            hold_condition(t, kwargs["cond_id"], reason=kwargs["reason"], until=kwargs["until"], new_condition=None, today=TODAY, entry_id="j1")
        assert err.value.code == code
    t = hold_condition(t, loss, reason="Chờ KQKD quý 4", until=in30, new_condition=None, today=TODAY, entry_id="j1")
    assert t["history"][-1] == {"type": "hold", "condition": loss, "kind": "loss_vs_cost", "on": "2026-11-02", "reason": "Chờ KQKD quý 4",
                                "broken_on": "2026-11-02", "broken_price": "40000", "until": "2026-12-02", "entry_id": "j1"}
    t, ev = advance(t, {loss: BROKEN, fs: BROKEN}, today=TODAY + timedelta(days=5), price=D("30000"))
    assert [(e["type"], e["condition"]["kind"]) for e in ev] == [("first", "f_score")]  # the other condition still reports
    t = mark_sent(t, ev)
    t, ev = advance(t, {loss: BROKEN, fs: BROKEN}, today=TODAY + timedelta(days=31), price=D("30000"))
    assert [(e["type"], e["condition"]["kind"]) for e in ev] == [("review", "loss_vs_cost")]
    t = mark_sent(t, ev)
    t, ev = advance(t, {loss: BROKEN, fs: BROKEN}, today=TODAY + timedelta(days=32), price=D("30000"))
    assert [e["type"] for e in ev] == ["step"] and ev[0]["condition"]["kind"] == "loss_vs_cost"  # reminders resume after the date


def test_holding_on_with_a_new_condition_replaces_the_broken_one_and_keeps_it_in_history():
    t = _thesis(("loss_vs_cost", {"pct": "10"}))
    loss = _ids(t)[0]
    t, ev = advance(t, {loss: BROKEN}, today=TODAY, price=D("40000"))
    t = mark_sent(t, ev)
    t = hold_condition(t, loss, reason="Nới ngưỡng vì đã mua thêm", until=None, today=TODAY, entry_id="j2",
                       new_condition={"kind": "loss_vs_cost", "params": {"pct": "25"}}, company="other")
    assert len(t["conditions"]) == 1 and t["conditions"][0]["id"] != loss and t["conditions"][0]["params"] == {"pct": "25"}
    assert t["conditions"][0]["status"] is None and t["conditions"][0]["set_on"] == "2026-11-02"
    assert t["history"][0]["id"] == loss and t["history"][0]["ended_by"] == "hold" and t["history"][1]["type"] == "hold"


def test_editing_keeps_broken_conditions_and_versions_the_rest():
    t = _thesis(("loss_vs_cost", {"pct": "10"}), ("f_score", {"n": 3}), fair="60000")
    loss, fs = _ids(t)
    t, ev = advance(t, {loss: BROKEN}, today=TODAY, price=D("40000"))
    base = {"reasons": ["cheap"], "note": "Rẻ"}
    for conds in ([{"id": fs, "kind": "f_score", "params": {"n": 3}}],  # dropping the broken one
                  [{"id": loss, "kind": "loss_vs_cost", "params": {"pct": "30"}}, {"id": fs, "kind": "f_score", "params": {"n": 3}}]):
        with pytest.raises(ThesisError) as err:
            edit_thesis(t, {**base, "conditions": conds}, company="other", today=TODAY, fair="60000")
        assert err.value.code == "broken_locked"
    t = edit_thesis(t, {**base, "note": "Rẻ, thêm điều kiện", "conditions": [
        {"id": loss, "kind": "loss_vs_cost", "params": {"pct": "10"}}, {"id": fs, "kind": "f_score", "params": {"n": 4}},
        {"kind": "fair_cut", "params": {"pct": "15"}}]}, company="other", today=TODAY, fair="58000")
    assert t["version"] == 2 and t["note"] == "Rẻ, thêm điều kiện"
    assert t["conditions"][0]["status"] == "broken" and t["conditions"][0]["id"] == loss  # untouched
    assert t["conditions"][1]["params"] == {"n": 4} and t["conditions"][1]["id"] != fs and t["history"][-1]["id"] == fs
    assert t["conditions"][2]["fair_at_set"] == "58000"


def _points(values, start=datetime(2018, 1, 2)):
    return [(start + timedelta(days=i), v) for i, v in enumerate(values)]


def test_the_deepest_past_fall_priced_on_the_current_position_is_a_scenario_not_a_forecast():
    out = scenario(_points([10, 12, 6, 9, 11]), price=D("40000"), shares=1000)
    assert out == {"depth": "-0.5000", "peak": "2018-01-03", "trough": "2018-01-04", "loss": "20000000"}
    assert scenario([], price=D("40000"), shares=1000) is None
    assert scenario(_points([10, 12]), price=None, shares=1000)["loss"] is None


def test_similar_past_situations_need_five_occurrences_six_months_apart():
    one_cycle = [20.0] * 5 + [17.0] * 5 + [15.0] * 130  # a close below 18, then six months later
    out = similar(_points(one_cycle * 5), "close_below", {"level": "18"})
    assert out == {"count": 5, "median": "-0.1176", "horizon": 126}  # 15 / 17 − 1
    assert similar(_points(one_cycle * 2), "close_below", {"level": "18"}) == {"count": 2, "median": None, "horizon": 126}
    assert similar(_points(one_cycle), "loss_vs_cost", {"pct": "10"}) is None  # no history for the owner's own cost
    wave = [10 + (i / 40) ** 2 for i in range(400)]
    wave = wave + [wave[-1] - i * 0.2 for i in range(1, 200)]  # stays above zero
    weekly = similar(_points(wave), "macd_weekly", {})
    assert weekly["count"] == 1 and weekly["median"] is None  # one weekly cross down, six months of data after it


def test_a_thesis_saved_while_a_condition_is_already_broken_reports_it_at_once():
    t = _thesis(("loss_vs_cost", {"pct": "10"}), fair="60000")
    assert t["conditions"][0]["set_on"] == "2026-11-02" and t["snapshot"]["price"] == "50000" and t["version"] == 1
    t, ev = advance(t, {_ids(t)[0]: BROKEN}, today=TODAY, price=D("40000"))
    assert ev[0]["type"] == "first" and t["conditions"][0]["broken_on"] == TODAY.isoformat()
