import json

import pytest

from investment_agent.domain.investable_capital import FinancialProfile, assess_capital
from investment_agent.domain.risk import (
    InvalidQuestionnaire, InvalidRiskAnswers, assess_risk, classify_total, load_questionnaire, QUESTIONNAIRE_PATH,
)


@pytest.fixture(scope="module")
def questionnaire():
    return load_questionnaire()


def answers_for(total=None, **overrides):
    """Answers summing to total (default all C), with per-question overrides like q4="A"."""
    keys = {n: "C" for n in range(1, 14)}
    if total is not None:
        points, keys = [1] * 13, {}
        remaining = total - 13
        for i in range(13):
            add = min(3, remaining)
            points[i] += add
            remaining -= add
        keys = {i + 1: "ABCD"[p - 1] for i, p in enumerate(points)}
    for name, value in overrides.items():
        keys[int(name[1:])] = value
    return [{"question": n, "answer": a} for n, a in keys.items()]


@pytest.mark.parametrize("total, group", [(13, "very_safe"), (19, "very_safe"), (20, "cautious"), (26, "cautious"),
                                          (27, "moderately_cautious"), (33, "moderately_cautious"), (34, "balanced"),
                                          (40, "balanced"), (41, "growth"), (46, "growth"), (47, "strong_growth"),
                                          (52, "strong_growth")])
def test_every_group_boundary(questionnaire, total, group):
    assert classify_total(total) == group
    result = assess_risk(questionnaire, answers_for(total))
    assert (result.total, result.group) == (total, group)


@pytest.mark.parametrize("total", [12, 53, True, 30.0])
def test_invalid_totals(total):
    with pytest.raises(ValueError):
        classify_total(total)


@pytest.mark.parametrize("answers", [
    answers_for()[:12],
    answers_for() + [{"question": 1, "answer": "A"}],
    answers_for()[:12] + [{"question": 14, "answer": "A"}],
    answers_for()[:12] + [{"question": 13, "answer": "E"}],
    answers_for()[:12] + [{"question": 13, "answer": "a"}],
    answers_for()[:12] + [{"question": "13", "answer": "A"}],
])
def test_missing_duplicate_or_out_of_range_answers_rejected(questionnaire, answers):
    with pytest.raises(InvalidRiskAnswers):
        assess_risk(questionnaire, answers)


def codes(result):
    return {flag.code for flag in result.flags}


@pytest.mark.parametrize("question", [4, 7])
def test_high_total_still_blocked_by_capacity_flag(questionnaire, question):
    result = assess_risk(questionnaire, answers_for(52, **{f"q{question}": "A"}))
    assert (result.total, result.group) == (49, "strong_growth")
    assert result.blocks_capital_increase is True
    assert codes(result) >= {"capacity_shortfall"}


def test_independent_review_flags(questionnaire):
    assert codes(assess_risk(questionnaire, answers_for(q6="A"))) == {"emergency_review"}
    assert codes(assess_risk(questionnaire, answers_for(q2="A"))) == {"near_term_money"}
    assert codes(assess_risk(questionnaire, answers_for(q3="A"))) == {"near_term_money"}
    clean = assess_risk(questionnaire, answers_for())
    assert clean.flags == () and clean.ready_for_allocation and not clean.blocks_capital_increase


@pytest.mark.parametrize("later", [{"q11": "D"}, {"q13": "D"}, {"q11": "D", "q13": "D"}])
def test_loss_tolerance_conflict_requires_confirmation(questionnaire, later):
    result = assess_risk(questionnaire, answers_for(q10="A", **later))
    assert result.unresolved_conflicts == ("answer_conflict_loss_tolerance",)
    assert result.ready_for_allocation is False
    confirmed = assess_risk(questionnaire, answers_for(q10="A", **later), confirmed_conflicts=["answer_conflict_loss_tolerance"])
    assert confirmed.unresolved_conflicts == () and confirmed.ready_for_allocation
    assert "answer_conflict_loss_tolerance" in codes(confirmed)


def test_profile_contradicting_emergency_answer_requires_confirmation(questionnaire):
    profile = FinancialProfile.model_validate({"as_of": "2026-10-25", "emergency_reserve": "200000000",
        "assets": [{"asset_id": "stocks", "kind": "equity", "amount": "500000000", "liquidity": "liquid",
                    "earmarks": [{"purpose": "emergency", "amount": "200000000"}]}]})
    capital = assess_capital(profile, ledger_value=None)
    result = assess_risk(questionnaire, answers_for(q6="D"), capital=capital)
    assert result.unresolved_conflicts == ("profile_conflict_emergency",)
    assert assess_risk(questionnaire, answers_for(q6="A"), capital=capital).unresolved_conflicts == ()


def test_confirming_unknown_conflict_is_rejected(questionnaire):
    with pytest.raises(InvalidRiskAnswers):
        assess_risk(questionnaire, answers_for(), confirmed_conflicts=["made_up"])


def test_result_records_full_answers_version_and_unvalidated_label(questionnaire):
    result = assess_risk(questionnaire, list(reversed(answers_for(q1="D"))))
    body = result.model_dump(mode="json")
    assert [a["question"] for a in body["answers"]] == list(range(1, 14))
    assert body["questionnaire_version"] == "risk-vi-2026-10-24.1"
    assert len(body["questionnaire_digest"]) == 64
    assert body["validation_status"] == "draft_unvalidated"


def test_questionnaire_matches_design_and_is_pinned(questionnaire, tmp_path):
    assert len(questionnaire.questions) == 13
    assert all([o.points for o in q.options] == [1, 2, 3, 4] for q in questionnaire.questions)
    data = json.loads(QUESTIONNAIRE_PATH.read_text(encoding="utf-8"))
    data["questions"][9]["options"][0]["text"] = "Đến 50 triệu"
    altered = tmp_path / "risk.json"
    altered.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(InvalidQuestionnaire):
        load_questionnaire(altered)
