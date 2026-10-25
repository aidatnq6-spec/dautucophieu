from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.valuation.assumptions import AssumptionError, ValuationAssumptions, approve_assumptions
from investment_agent.valuation.dcf import discounted_value, sensitivity, value_assumptions
from investment_agent.valuation.dividends import ddm_value

NOW = datetime(2026, 10, 25, 9, tzinfo=timezone.utc)
TOL = Decimal("1e-18")


def scenario(flows=("100", "110", "121"), rate="0.10", growth="0"):
    return {"cash_flows": list(flows), "discount_rate": rate, "terminal_growth": growth}


def assumptions(model="fcff_dcf", **changes):
    data = {"entity_id": "ent-fpt", "model": model, "valuation_date": "2026-10-23",
            "scenarios": {"down": scenario(rate="0.12"), "base": scenario(), "up": scenario(rate="0.09")},
            "net_debt": "200", "minority_interest": "30", "non_operating_assets": "50", "shares": 10,
            "reinvestment_note": "Capex duy trì 5% doanh thu", "sources": ["doc-bctc-2025"]}
    data.update(changes)
    return ValuationAssumptions.model_validate(data)


def test_present_value_matches_hand_calculation():
    # 100/1.1 + 110/1.1² + 121/1.1³ = 3 × 1000/11 ; terminal 121/0.10 discounted 3 years = 10000/11
    pv = discounted_value(assumptions().scenarios["base"])
    assert abs(pv.explicit - Decimal(3000) / 11) < TOL
    assert abs(pv.terminal - Decimal(10000) / 11) < TOL
    assert abs(pv.total - Decimal(13000) / 11) < TOL


@pytest.mark.parametrize("growth", ["0.10", "0.11"])
def test_terminal_growth_not_below_discount_rejected(growth):
    with pytest.raises(ValidationError):
        assumptions(scenarios={"down": scenario(), "base": scenario(growth=growth), "up": scenario()})


def test_fcff_subtracts_net_debt_and_minority_once_and_adds_non_operating():
    result = value_assumptions(approve_assumptions(assumptions(), actor="owner", now=NOW))
    base = result.scenarios["base"]
    assert abs(base.equity_value - (Decimal(13000) / 11 - 200 - 30 + 50)) < TOL
    assert abs(base.per_share - base.equity_value / 10) < TOL


@pytest.mark.parametrize("model", ["fcfe_dcf", "ddm"])
def test_equity_models_do_not_subtract_net_debt_again(model):
    result = value_assumptions(approve_assumptions(assumptions(model=model, net_debt=None, minority_interest=None, non_operating_assets=None),
                                                   actor="owner", now=NOW))
    assert abs(result.scenarios["base"].equity_value - Decimal(13000) / 11) < TOL


def test_fcfe_adds_non_operating_assets_but_ddm_rejects_them():
    fcfe = value_assumptions(assumptions(model="fcfe_dcf", net_debt=None, minority_interest=None))
    assert abs(fcfe.scenarios["base"].equity_value - (Decimal(13000) / 11 + 50)) < TOL
    with pytest.raises(ValidationError):
        assumptions(model="ddm", net_debt=None, minority_interest=None)


def test_equity_model_rejects_net_debt_input_to_avoid_double_count():
    with pytest.raises(ValidationError):
        assumptions(model="fcfe_dcf")


def test_draft_assumptions_produce_labelled_value_but_no_active_zone():
    result = value_assumptions(assumptions())
    assert result.status == "draft" and result.buy_zone_active is False
    approved = value_assumptions(approve_assumptions(assumptions(), actor="owner", now=NOW))
    assert approved.status == "approved" and approved.buy_zone_active is True


def test_scenarios_are_ordered_and_all_three_required():
    with pytest.raises(ValidationError):
        assumptions(scenarios={"base": scenario()})
    result = value_assumptions(assumptions())
    assert result.scenarios["down"].per_share < result.scenarios["base"].per_share < result.scenarios["up"].per_share


def test_higher_discount_lowers_value_for_positive_flows():
    values = sensitivity(assumptions().scenarios["base"], [Decimal("0.08"), Decimal("0.10"), Decimal("0.12")])
    assert values[0] > values[1] > values[2]


@pytest.mark.parametrize("changes, reason", [
    ({"net_debt": None}, "net_debt_missing"),
    ({"shares": None}, "shares_missing"),
])
def test_missing_required_inputs_are_unavailable_not_defaulted(changes, reason):
    result = value_assumptions(assumptions(**changes))
    assert result.status == "unavailable" and result.reason == reason and result.scenarios == {}


def test_empty_forecast_rejected():
    with pytest.raises(ValidationError):
        assumptions(scenarios={"down": scenario(flows=()), "base": scenario(), "up": scenario()})


def test_approval_is_owner_only_and_immutable():
    with pytest.raises(AssumptionError):
        approve_assumptions(assumptions(), actor="ai", now=NOW)
    approved = approve_assumptions(assumptions(), actor="owner", now=NOW)
    with pytest.raises(ValidationError):
        approved.net_debt = Decimal(1)
    with pytest.raises(AssumptionError):
        approve_assumptions(approved, actor="owner", now=NOW)
    assert approved.content_digest == assumptions().content_digest


def test_ddm_rejects_negative_dividends():
    with pytest.raises(ValueError):
        ddm_value(assumptions(model="ddm", net_debt=None, minority_interest=None, non_operating_assets=None,
                  scenarios={"down": scenario(flows=("-1", "1")), "base": scenario(), "up": scenario()}).scenarios["down"])
