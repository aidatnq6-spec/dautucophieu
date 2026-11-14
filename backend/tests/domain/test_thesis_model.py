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
