import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from investment_agent.domain.allocation import POLICY_PATH, Position, evaluate_allocation, load_allocation_policy
from investment_agent.domain.exception_review import ExceptionReview, loss_scenarios, review_exception
from investment_agent.domain.investable_capital import FinancialProfile, assess_capital
from investment_agent.domain.pinned import InvalidPolicy
from investment_agent.domain.profile import profile_freshness
from investment_agent.domain.risk import assess_risk, load_questionnaire

NOW = datetime(2026, 10, 25, 9, tzinfo=timezone.utc)
M = Decimal(1_000_000)
GROUP_ANSWERS = {"very_safe": "A" * 13, "cautious": "B" * 7 + "A" * 6, "moderately_cautious": "B" * 12 + "C",
                 "balanced": "C" * 13, "growth": "C" * 10 + "DDD", "strong_growth": "D" * 13}


@pytest.fixture(scope="module")
def policy():
    return load_allocation_policy()


def capital(millions=1000, reserve=0):
    profile = FinancialProfile.model_validate({"as_of": "2026-10-25", "emergency_reserve": str(reserve * 1_000_000),
        "assets": [{"asset_id": "cash", "kind": "deposit", "amount": str((millions + reserve) * 1_000_000), "liquidity": "liquid",
                    "earmarks": [{"purpose": "emergency", "amount": str(reserve * 1_000_000)}] if reserve else []}]})
    return assess_capital(profile, ledger_value=None)


def risk(group="strong_growth", **overrides):
    letters = list(GROUP_ANSWERS[group])
    for key, value in overrides.items():
        letters[int(key[1:]) - 1] = value
    return assess_risk(load_questionnaire(), [{"question": i + 1, "answer": a} for i, a in enumerate(letters)])


FRESH = profile_freshness(NOW - timedelta(days=1), NOW)


def pos(issuer, millions, industry="bank", control=None):
    return Position(issuer_id=issuer, control_group_id=control or issuer, industry=industry, market_value=str(Decimal(millions) * M))


def diversified(total_millions, *, n=8, industries=4):
    each = Decimal(total_millions) / n
    return [pos(f"I{i}", each, industry=f"ind{i % industries}") for i in range(n)]


def evaluate(policy, *, group="strong_growth", holdings=(), buys=(), cap=None, review=None, ratio=None, fresh=FRESH, risk_result=None, cash=None):
    return evaluate_allocation(policy, capital=cap or capital(), risk=risk_result or risk(group), freshness=fresh,
                               holdings=list(holdings), buys=list(buys), exception=review, exception_ratio=ratio, available_cash=cash, now=NOW)


@pytest.mark.parametrize("group, ratio", [("very_safe", "0"), ("cautious", "0.10"), ("moderately_cautious", "0.25"),
                                          ("balanced", "0.35"), ("growth", "0.50"), ("strong_growth", "0.60")])
def test_baseline_targets_by_group(policy, group, ratio):
    result = evaluate(policy, group=group)
    assert result.risk_group == group and result.target_ratio == Decimal(ratio)
    assert result.long_term_target_value == Decimal(ratio) * 1000 * M
    assert result.policy_version == "allocation-2026-10-25.1"


def test_non_positive_capital_never_divides(policy):
    result = evaluate(policy, cap=capital(0, reserve=100))
    assert result.status == "blocked" and "capital_not_ready" in result.violations
    assert result.target_ratio is None and result.current_ratio is None and result.max_new_buy == 0


def test_current_ratio_and_headroom_split_target_from_deployable_now(policy):
    result = evaluate(policy, group="balanced", holdings=[pos("A", 100)], cash=str(50 * M))
    assert result.current_ratio == Decimal("0.1")
    assert result.max_new_buy == 250 * M and result.deployable_now == 50 * M


def test_unknown_cash_leaves_deployable_unknown(policy):
    assert evaluate(policy, group="balanced").deployable_now is None


@pytest.mark.parametrize("group", ["very_safe", "cautious", "moderately_cautious", "balanced", "growth"])
def test_lower_groups_cannot_buy_above_baseline_even_with_review(policy, group):
    target = load_allocation_policy().baseline_equity[group] * 1000 * M
    result = evaluate(policy, group=group, buys=[pos("A", target / M + 1)], ratio=Decimal("0.7"))
    assert result.status == "blocked"
    assert {"exception_not_eligible", "exceeds_target"} <= set(result.violations)


def test_buy_within_baseline_is_ok(policy):
    result = evaluate(policy, group="growth", holdings=[pos("A", 200)], buys=[pos("B", 300)])
    assert result.status == "ok" and result.violations == ()


def test_post_trade_portfolio_is_checked_not_individual_orders(policy):
    result = evaluate(policy, group="growth", holdings=[pos("A", 400)], buys=[pos("B", 60), pos("C", 60)])
    assert result.status == "blocked" and result.violations == ("exceeds_target",)


@pytest.mark.parametrize("flag", ["q4", "q7"])
def test_capacity_flag_blocks_new_buys_even_within_baseline(policy, flag):
    result = evaluate(policy, risk_result=risk("strong_growth", **{flag: "A"}), buys=[pos("A", 10)])
    assert "capacity_blocks_increase" in result.violations and result.max_new_buy == 0


def test_unresolved_risk_conflict_and_stale_profile_block_proposals(policy):
    conflicted = risk("strong_growth", q10="A")
    assert "risk_needs_confirmation" in evaluate(policy, risk_result=conflicted).violations
    stale = profile_freshness(NOW - timedelta(days=40), NOW)
    assert "profile_reconfirm_required" in evaluate(policy, fresh=stale).violations


def test_price_rise_above_target_warns_without_sell_order(policy):
    result = evaluate(policy, group="balanced", holdings=[pos("A", 500)])
    assert result.status == "ok" and result.max_new_buy == 0
    assert [(w.code, w.amount) for w in result.warnings] == [("above_target_from_price", 150 * M)]
    assert not hasattr(result, "sell_orders")


# --- exception -------------------------------------------------------------

def scenarios(policy, ratio="0.9"):
    return [s.drop for s in loss_scenarios(policy, capital(), Decimal(ratio))]


def full_review(policy, **changes):
    data = {"holding_extension_confirmed": True, "holding_extension_reason": "Có lương ổn định, mục tiêu nhà sau 8 năm",
            "funds_not_borrowed": True, "reserve_confirmed": True, "cashflow_reviewed_at": "2026-10-20",
            "untouched_at_least_one_year": True, "acknowledged_scenarios": ["0.30", "0.50", "0.60"],
            "confirmed_at": (NOW - timedelta(days=1)).isoformat()}
    data.update(changes)
    return ExceptionReview.model_validate(data)


def test_loss_scenarios_show_effect_on_whole_capital(policy):
    rows = loss_scenarios(policy, capital(), Decimal("0.9"))
    assert [(r.drop, r.equity_loss, r.capital_after, r.share_of_capital) for r in rows] == [
        (Decimal("0.30"), 270 * M, 730 * M, Decimal("0.27")),
        (Decimal("0.50"), 450 * M, 550 * M, Decimal("0.45")),
        (Decimal("0.60"), 540 * M, 460 * M, Decimal("0.54"))]


def test_complete_exception_allows_up_to_90_percent_diversified(policy):
    result = evaluate(policy, buys=diversified(900), review=full_review(policy), ratio=Decimal("0.9"))
    assert result.status == "ok", result.violations
    assert result.target_ratio == Decimal("0.9") and result.exception_applied


def test_exception_cannot_exceed_90_percent(policy):
    result = evaluate(policy, buys=diversified(900), review=full_review(policy), ratio=Decimal("0.91"))
    assert "exceeds_exception_cap" in result.violations


@pytest.mark.parametrize("changes, code", [
    ({"holding_extension_confirmed": False}, "holding_extension"),
    ({"holding_extension_reason": " "}, "holding_extension"),
    ({"funds_not_borrowed": False}, "borrowed_funds"),
    ({"reserve_confirmed": False}, "reserve"),
    ({"untouched_at_least_one_year": False}, "untouched_one_year"),
    ({"acknowledged_scenarios": ["0.30", "0.50"]}, "loss_scenarios"),
    ({"confirmed_at": (NOW - timedelta(days=40)).isoformat()}, "review_expired"),
    ({"cashflow_reviewed_at": "2026-08-01"}, "cashflow_outdated"),
])
def test_any_missing_exception_condition_blocks(policy, changes, code):
    missing = review_exception(policy, full_review(policy, **changes), risk=risk(), capital=capital(), now=NOW)
    assert code in missing
    result = evaluate(policy, buys=diversified(900), review=full_review(policy, **changes), ratio=Decimal("0.9"))
    assert result.status == "blocked" and "exception_review_incomplete" in result.violations


def test_reserve_warning_blocks_exception(policy):
    weak = assess_capital(FinancialProfile.model_validate({"as_of": "2026-10-25", "emergency_reserve": "100000000",
        "assets": [{"asset_id": "cash", "kind": "deposit", "amount": "1100000000", "liquidity": "liquid"}]}), ledger_value=None)
    assert "reserve" in review_exception(policy, full_review(policy), risk=risk(), capital=weak, now=NOW)


def test_missing_review_falls_back_to_baseline(policy):
    result = evaluate(policy, buys=diversified(900), ratio=Decimal("0.9"))
    assert result.status == "blocked" and result.target_ratio == Decimal("0.60")


@pytest.mark.parametrize("buys, code", [
    (diversified(700, n=7), "too_few_issuers"),
    (diversified(900, industries=3), "too_few_industries"),
    (diversified(800) + [pos("I0", 60, industry="ind0")], "issuer_concentration"),
    ([pos(f"I{i}", 112.5, industry="bank" if i < 3 else f"x{i}") for i in range(8)], "industry_concentration"),
    ([pos(f"I{i}", 112.5, industry=f"ind{i % 4}", control="GROUP" if i < 2 else None) for i in range(8)], "too_few_issuers"),
])
def test_diversification_limits_on_post_trade_portfolio(policy, buys, code):
    result = evaluate(policy, buys=buys, review=full_review(policy), ratio=Decimal("0.9"))
    assert code in result.violations


def test_same_control_group_is_combined_for_concentration(policy):
    buys = diversified(800, n=9) + [pos("SISTER", 70, industry="ind0", control="I0")]
    result = evaluate(policy, buys=buys, review=full_review(policy), ratio=Decimal("0.9"))
    assert "issuer_concentration" in result.violations


@pytest.mark.parametrize("field", ["industry", "control_group_id"])
def test_missing_industry_or_control_data_is_not_diversified(policy, field):
    buys = diversified(900)
    buys[0] = buys[0].model_copy(update={field: None})
    result = evaluate(policy, buys=buys, review=full_review(policy), ratio=Decimal("0.9"))
    assert "diversification_data_missing" in result.violations


def test_policy_is_pinned(tmp_path):
    data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    data["exception"]["max_equity"] = "0.95"
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InvalidPolicy):
        load_allocation_policy(path)
