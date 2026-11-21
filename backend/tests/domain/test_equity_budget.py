from decimal import Decimal

from investment_agent.domain.equity_budget import equity_budget

RATIOS = {"cautious": Decimal("0.10"), "growth": Decimal("0.50")}


def test_budget_is_total_less_protected_needs_times_the_group_ratio_with_room_left_at_cost():
    b = equity_budget(total=Decimal("2000000000"), deductions=Decimal("300000000"), group="growth", ratios=RATIOS, held_cost=Decimal("600000000"))
    assert b["status"] == "ok" and b["base"] == "1700000000" and b["ratio"] == "0.50" and b["budget"] == "850000000"
    assert b["held_cost"] == "600000000" and b["held_weight"] == "0.7059" and b["room"] == "250000000" and b["over"] is None


def test_holding_more_than_the_budget_reports_the_excess_only():
    b = equity_budget(total=Decimal("1000000000"), deductions=Decimal("0"), group="cautious", ratios=RATIOS, held_cost=Decimal("150000000"))
    assert b["budget"] == "100000000" and b["room"] is None and b["over"] == "50000000"


def test_deductions_never_make_the_base_negative():
    b = equity_budget(total=Decimal("100"), deductions=Decimal("500"), group="growth", ratios=RATIOS, held_cost=Decimal("0"))
    assert b["base"] == "0" and b["budget"] == "0" and b["held_weight"] is None and b["room"] == "0"


def test_room_and_weight_follow_the_market_value_when_given_with_the_cost_kept_beside_it():
    """Owner, 21/11/2026: holdings at market price, so the room left reflects what the stocks are worth today."""
    b = equity_budget(total=Decimal("2000000000"), deductions=Decimal("300000000"), group="growth", ratios=RATIOS, held_cost=Decimal("600000000"),
                      held_value=Decimal("900000000"))
    assert b["held_cost"] == "600000000" and b["held_value"] == "900000000" and b["held_weight"] == "1.0588"
    assert b["room"] is None and b["over"] == "50000000"


def test_missing_total_or_risk_group_says_so_instead_of_guessing():
    assert equity_budget(total=None, deductions=Decimal("0"), group="growth", ratios=RATIOS, held_cost=Decimal("0"))["status"] == "no_total"
    assert equity_budget(total=Decimal("1"), deductions=Decimal("0"), group=None, ratios=RATIOS, held_cost=Decimal("0"))["status"] == "no_risk"
