from datetime import date, timedelta
from decimal import Decimal

import pytest

from investment_agent.domain.thesis import ThesisError, evaluate, validate_thesis

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
