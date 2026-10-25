from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.domain.investable_capital import FinancialProfile, assess_capital
from investment_agent.domain.profile import profile_freshness

AS_OF = "2026-10-25"
M = 1_000_000


def vnd(millions):
    return str(millions * M)


def asset(asset_id, millions, **extra):
    return {"asset_id": asset_id, "kind": "deposit", "amount": vnd(millions), "liquidity": "liquid", **extra}


def goal(goal_id, millions, due, **extra):
    return {"goal_id": goal_id, "due_date": due, "amount": vnd(millions), "preserve_capital": False,
            "deferrable": False, "confirmed": True, **extra}


def profile(**changes):
    data = {"as_of": AS_OF, "emergency_reserve": vnd(200),
            "assets": [asset("savings", 800, earmarks=[{"purpose": "emergency", "amount": vnd(200)}])],
            "goals": [goal("tuition", 100, "2027-06-01")], "funding_sources": []}
    data.update(changes)
    return FinancialProfile.model_validate(data)


def lines(result, kind):
    return {line.ref: line.amount for line in result.lines if line.kind == kind}


def test_reserve_and_unfunded_need_are_deducted_once():
    result = assess_capital(profile(), ledger_value=None)
    assert result.status == "ready"
    assert result.investable_capital == Decimal(vnd(500))
    assert lines(result, "deduction") == {"emergency_reserve": Decimal(vnd(200)), "tuition": Decimal(vnd(100))}
    assert result.gross_included == Decimal(vnd(800)) and result.deductions_total == Decimal(vnd(300))


def test_ledger_tracked_cash_and_stocks_are_not_counted_twice():
    assets = [asset("savings", 500, earmarks=[{"purpose": "emergency", "amount": vnd(200)}]),
              asset("broker", 300, kind="equity", ledger_link="ledger-main")]
    result = assess_capital(profile(assets=assets), ledger_value=Decimal(vnd(300)))
    assert result.investable_capital == Decimal(vnd(500))
    assert lines(result, "included") == {"savings": Decimal(vnd(500)), "ledger": Decimal(vnd(300))}
    assert lines(result, "excluded") == {"broker": Decimal(vnd(300))}


def test_missing_ledger_valuation_is_incomplete_not_zero():
    assets = [asset("broker", 300, kind="equity", ledger_link="ledger-main")]
    result = assess_capital(profile(assets=assets, emergency_reserve="0"), ledger_value=None)
    assert result.status == "incomplete" and result.investable_capital is None


def test_recurring_spending_already_funded_is_not_deducted_again():
    funded = goal("living", 240, "2027-10-01", funding=[{"source_id": "salary", "amount": vnd(240)}])
    result = assess_capital(profile(goals=[funded], funding_sources=[{"source_id": "salary", "amount": vnd(240)}]), ledger_value=None)
    assert result.investable_capital == Decimal(vnd(600))
    assert "living" not in lines(result, "deduction")


def test_partially_funded_goal_deducts_only_shortfall():
    partial = goal("car", 300, "2027-03-01", funding=[{"source_id": "bonus", "amount": vnd(120)}])
    result = assess_capital(profile(goals=[partial], funding_sources=[{"source_id": "bonus", "amount": vnd(120)}]), ledger_value=None)
    assert lines(result, "deduction")["car"] == Decimal(vnd(180))


def test_preserved_goal_after_24_months_is_still_separated():
    house = goal("house", 150, "2028-10-01", preserve_capital=True, deferrable=True)
    result = assess_capital(profile(goals=[house]), ledger_value=None)
    assert lines(result, "deduction")["house"] == Decimal(vnd(150))
    assert result.investable_capital == Decimal(vnd(450))


def test_flexible_goal_beyond_12_months_is_listed_not_deducted():
    trip = goal("trip", 50, "2028-10-01", deferrable=True)
    result = assess_capital(profile(goals=[trip]), ledger_value=None)
    assert lines(result, "not_deducted") == {"trip": Decimal(vnd(50))}
    assert result.investable_capital == Decimal(vnd(600))


def test_twelve_month_boundary_is_inclusive():
    edge = goal("edge", 10, "2027-10-25", deferrable=True)
    later = goal("later", 10, "2027-10-26", deferrable=True)
    result = assess_capital(profile(goals=[edge, later]), ledger_value=None)
    assert "edge" in lines(result, "deduction") and "later" in lines(result, "not_deducted")


def test_unconfirmed_goal_blocks_capital():
    result = assess_capital(profile(goals=[goal("unsure", 10, "2027-01-01", confirmed=False)]), ledger_value=None)
    assert result.status == "needs_confirmation" and result.investable_capital is None


@pytest.mark.parametrize("reserve, need", [(800, 0), (700, 150)])
def test_nonpositive_capital_is_not_suitable_without_division(reserve, need):
    goals = [goal("need", need, "2027-01-01")] if need else []
    savings = asset("savings", 800, earmarks=[{"purpose": "emergency", "amount": vnd(min(reserve, 800))}])
    result = assess_capital(profile(emergency_reserve=vnd(reserve), assets=[savings], goals=goals), ledger_value=None)
    assert result.status == "not_suitable" and result.investable_capital is None
    assert result.shortfall == Decimal(vnd(reserve + need - 800))


def test_illiquid_and_consumption_assets_are_excluded_by_default():
    assets = [asset("savings", 800, earmarks=[{"purpose": "emergency", "amount": vnd(200)}]),
              asset("home", 3000, kind="real_estate", liquidity="consumption"),
              asset("land", 500, kind="real_estate", liquidity="illiquid")]
    result = assess_capital(profile(assets=assets), ledger_value=None)
    assert result.investable_capital == Decimal(vnd(500))
    assert set(lines(result, "excluded")) == {"home", "land"}


def test_emergency_reserve_held_in_stocks_warns_liquidity_shortfall():
    assets = [asset("savings", 500, earmarks=[{"purpose": "emergency", "amount": vnd(50)}]),
              asset("stocks", 300, kind="equity", earmarks=[{"purpose": "emergency", "amount": vnd(150)}])]
    result = assess_capital(profile(assets=assets), ledger_value=None)
    codes = {w.code: w.amount for w in result.warnings}
    assert codes == {"emergency_reserve_not_liquid": Decimal(vnd(150)), "emergency_reserve_shortfall": Decimal(vnd(150))}
    assert lines(result, "deduction")["emergency_reserve"] == Decimal(vnd(200))


@pytest.mark.parametrize("changes", [
    {"goals": [goal("a", 100, "2027-01-01", funding=[{"source_id": "s", "amount": vnd(80)}]),
               goal("b", 100, "2027-01-01", funding=[{"source_id": "s", "amount": vnd(80)}])],
     "funding_sources": [{"source_id": "s", "amount": vnd(100)}]},
    {"goals": [goal("a", 100, "2027-01-01", funding=[{"source_id": "missing", "amount": vnd(1)}])]},
    {"goals": [goal("a", 100, "2027-01-01", funding=[{"source_id": "s", "amount": vnd(120)}])],
     "funding_sources": [{"source_id": "s", "amount": vnd(200)}]},
    {"assets": [asset("x", 1), asset("x", 2)]},
    {"goals": [goal("g", 1, "2027-01-01"), goal("g", 2, "2027-01-01")]},
    {"assets": [asset("x", 10, earmarks=[{"purpose": "emergency", "amount": vnd(11)}])]},
    {"assets": [asset("x", 10, earmarks=[{"purpose": "unknown-goal", "amount": vnd(1)}])]},
    {"emergency_reserve": 200000000.0},
    {"assets": [asset("x", 10, amount="-1")]},
])
def test_inconsistent_profiles_are_rejected(changes):
    with pytest.raises(ValidationError):
        profile(**changes)


def test_goal_earmark_on_asset_is_allowed():
    assets = [asset("savings", 800, earmarks=[{"purpose": "emergency", "amount": vnd(200)}, {"purpose": "tuition", "amount": vnd(100)}])]
    assert assess_capital(profile(assets=assets), ledger_value=None).investable_capital == Decimal(vnd(500))


def test_exact_decimal_amounts_survive_breakdown():
    result = assess_capital(profile(emergency_reserve="200000000.125", assets=[asset("savings", 800, amount="800000000.5",
                            earmarks=[{"purpose": "emergency", "amount": "200000000.125"}])]), ledger_value=None)
    assert result.investable_capital == Decimal("500000000.375")
    assert result.model_dump(mode="json")["investable_capital"] == "500000000.375"


CONFIRMED = datetime(2026, 9, 1, 3, tzinfo=timezone.utc)


@pytest.mark.parametrize("age_days, status, allowed", [(0, "current", True), (23, "current", True),
                                                        (24, "refresh_soon", True), (31, "refresh_soon", True),
                                                        (32, "reconfirm_required", False)])
def test_profile_freshness_blocks_new_recommendations_after_31_days(age_days, status, allowed):
    result = profile_freshness(CONFIRMED, CONFIRMED + timedelta(days=age_days))
    assert (result.status, result.allows_new_recommendations, result.allows_asset_report) == (status, allowed, True)


def test_profile_freshness_rejects_naive_or_future_confirmation():
    with pytest.raises(ValueError):
        profile_freshness(datetime(2026, 9, 1), CONFIRMED)
    assert profile_freshness(CONFIRMED + timedelta(days=1), CONFIRMED).allows_new_recommendations is False
