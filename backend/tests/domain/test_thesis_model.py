from datetime import date
from decimal import Decimal

import pytest

from investment_agent.domain.thesis_model import ModelError, grade, model_view, validate_model

SCEN = [{"name": "bad", "price": "44106", "prob": "25", "note": "HTIT chậm"}, {"name": "base", "price": "58136", "prob": "50", "note": ""},
        {"name": "good", "price": "61362", "prob": "25", "note": ""}]


def ind(**k):
    return {"id": "a", "name": "Hiệu suất HTIT", "tier": "coincident", "unit": "%", "bad": "60.1", "base": "66.4", "good": "72.7", "lower_better": False,
            "source": "manual", "readings": [{"period": "2026-Q3", "value": "66.7"}], **k}


def test_scenarios_need_three_prices_and_probabilities_adding_to_100():
    m = validate_model({"scenarios": SCEN, "review": {"when": "khi có số 2027", "on": "2027-03-31"}, "indicators": [ind()]})
    assert [s["name"] for s in m["scenarios"]] == ["bad", "base", "good"] and m["review"]["on"] == "2027-03-31"
    with pytest.raises(ModelError):
        validate_model({"scenarios": [{**SCEN[0], "prob": "30"}, SCEN[1], SCEN[2]], "indicators": []})
    with pytest.raises(ModelError):
        validate_model({"scenarios": [{**SCEN[0], "price": "-1"}, SCEN[1], SCEN[2]], "indicators": []})
    with pytest.raises(ModelError):
        validate_model({"scenarios": [], "indicators": [ind(source="auto:guess")]})
    assert validate_model({"scenarios": [], "indicators": []})["scenarios"] == []  # scenarios are optional, all three or none


def test_grading_follows_the_owner_s_rule_good_from_the_base_level_bad_at_the_bad_level():
    assert grade(Decimal("66.7"), bad=Decimal("60.1"), base=Decimal("66.4"), lower_better=False) == "good"
    assert grade(Decimal("63"), bad=Decimal("60.1"), base=Decimal("66.4"), lower_better=False) == "watch"
    assert grade(Decimal("60.1"), bad=Decimal("60.1"), base=Decimal("66.4"), lower_better=False) == "bad"
    assert grade(Decimal("11.3"), bad=Decimal("15.9"), base=Decimal("13.1"), lower_better=True) == "good"  # P/E: lower is better
    assert grade(Decimal("16"), bad=Decimal("15.9"), base=Decimal("13.1"), lower_better=True) == "bad"


def test_the_view_weighs_the_scenarios_against_the_latest_close_and_counts_the_lights():
    model = validate_model({"scenarios": SCEN, "review": {"when": "x", "on": "2026-11-10"},
                            "indicators": [ind(), ind(id="b", name="LN mẹ quý", unit="tỷ", bad="100", base="150", good="200", source="auto:npat_parent_q",
                                                  readings=[]),
                                           ind(id="c", name="Không có số", readings=[])]})
    v = model_view(model, close=Decimal("44400"), close_date="2026-11-13", auto={"npat_parent_q": ("2026-Q3", Decimal("120"))}, today=date(2026, 11, 14))
    s = v["scenarios"]
    assert s["expected"] == "55435" and s["upside"] == "0.2485" and s["review_due"] is True  # 0.25×44106 + 0.5×58136 + 0.25×61362
    assert [x["upside"] for x in s["rows"]] == ["-0.0066", "0.3094", "0.382"]
    rows = {r["id"]: r for r in v["indicators"]}
    assert rows["a"]["current"] == "66.7" and rows["a"]["period"] == "2026-Q3" and rows["a"]["grade"] == "good"
    assert rows["b"]["current"] == "120" and rows["b"]["grade"] == "watch" and rows["c"]["grade"] is None
    assert v["lights"] == {"good": 1, "watch": 1, "bad": 0, "none": 1}



def test_the_six_questions_keep_their_answers_and_gaps_and_count_the_open_ones():
    m = validate_model({"scenarios": [], "indicators": [], "stage": "reviewed", "questions": {
        "business": {"status": "good", "summary": "Hai nguồn mới", "points": ["Thuê hạ tầng 50 năm", ""], "gaps": [{"id": "g1", "text": "Tách sản lượng × giá", "ref": "PHP-01"}]},
        "valuation": {"status": "maybe", "gaps": [{"id": "g2", "text": "Giá ngầm định TEU", "done": True}]}}})
    assert m["stage"] == "reviewed" and list(m["questions"]) == ["business", "strategy", "industry", "valuation", "monitoring", "timing"]
    assert m["questions"]["business"]["points"] == ["Thuê hạ tầng 50 năm"] and m["questions"]["valuation"]["status"] is None  # unknown status dropped
    v = model_view(m, close=None, close_date=None, auto={}, today=date(2026, 11, 14))
    assert v["gaps"] == {"open": 1, "total": 2} and v["stage"] == "reviewed"
    with pytest.raises(ModelError):
        validate_model({"scenarios": [], "indicators": [], "questions": {"business": {"gaps": [{"id": "g", "text": " "}]}}})


def test_catalysts_have_a_sign_and_are_due_on_their_day_until_marked_done():
    m = validate_model({"scenarios": [], "indicators": [], "catalysts": [
        {"id": "c1", "when": "Q4/2026", "on": "2026-11-10", "sign": "+", "text": "Bàn giao hạ tầng đợt 3", "source": "ĐHĐCĐ 2026"},
        {"id": "c2", "when": "2028", "sign": "-", "text": "Bến 7&8 vào khai thác", "source": "FPTS"},
        {"id": "c3", "when": "Q3/2026", "on": "2026-09-30", "sign": "?", "text": "Góp vốn Bạch Đằng", "done": True}]})
    v = model_view(m, close=None, close_date=None, auto={}, today=date(2026, 11, 14))
    assert [c["id"] for c in v["catalysts"]] == ["c1", "c2", "c3"] and v["catalysts_due"] == ["c1"]
    with pytest.raises(ModelError):
        validate_model({"scenarios": [], "indicators": [], "catalysts": [{"id": "x", "text": "a", "sign": "!"}]})
