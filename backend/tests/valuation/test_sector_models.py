from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.valuation.cyclical import CyclicalInputs, value_cyclical
from investment_agent.valuation.nav import NavInputs, value_nav
from investment_agent.valuation.residual_income import ResidualIncomeInputs, value_residual_income
from investment_agent.valuation.selector import Comparable, IssuerEconomics, cross_check, select_model

TOL = Decimal("1e-15")
APPROVED = {"assumption_version": 3, "approved": True}


def ri(**changes):
    data = {"book_equity": "1000", "roe_path": ["0.12", "0.12", "0.12"], "payout_path": ["0.3", "0.3", "0.3"],
            "cost_of_equity": "0.12", "terminal": "fade_to_zero", "terminal_growth": "0",
            "capital_ratio_path": ["0.11", "0.11", "0.11"], "regulatory_minimum": "0.08", "shares": 10, **APPROVED}
    data.update(changes)
    return ResidualIncomeInputs.model_validate(data)


def test_roe_equal_to_cost_of_equity_gives_book_value():
    result = value_residual_income(ri())
    assert abs(result.equity_value - Decimal(1000)) < TOL and result.per_share == result.equity_value / 10


def test_zero_residual_income_with_perpetuity_still_book_value():
    assert abs(value_residual_income(ri(terminal="perpetuity", terminal_growth="0.02")).equity_value - 1000) < TOL


def test_residual_income_oracle_hand_calculated():
    # B0=1000, ROE 15%, ke 10%, payout 0 over 2 years, fade to zero:
    # RI1 = 0.05*1000 = 50 ; B1 = 1150 ; RI2 = 0.05*1150 = 57.5 ; value = 1000 + 50/1.1 + 57.5/1.21
    result = value_residual_income(ri(roe_path=["0.15", "0.15"], payout_path=["0", "0"], cost_of_equity="0.10",
                                      capital_ratio_path=["0.11", "0.11"]))
    expected = Decimal(1000) + Decimal(50) / Decimal("1.1") + Decimal("57.5") / Decimal("1.21")
    assert abs(result.equity_value - expected) < TOL


def test_regulatory_capital_breach_is_flagged_and_blocks_zone():
    result = value_residual_income(ri(capital_ratio_path=["0.11", "0.07", "0.09"]))
    assert "capital_below_regulatory_minimum" in result.flags and result.buy_zone_active is False


def test_path_lengths_must_match():
    with pytest.raises(ValidationError):
        ri(payout_path=["0.3"])


def nav(**changes):
    data = {"projects": [
        {"project_id": "p1", "ownership": "0.8", "probability": "0.9", "legal_status": "approved", "progress_note": "Đang bàn giao",
         "gross_value": "1000", "project_obligations": "200"},
        {"project_id": "p2", "ownership": "1", "probability": "0.5", "legal_status": "pending", "progress_note": "Chờ quy hoạch 1/500",
         "gross_value": "600", "project_obligations": "100"}],
        "corporate_net_debt_excluding_project_obligations": "150", "other_assets": "40", "minority_interest": "10", "shares": 10, **APPROVED}
    data.update(changes)
    return NavInputs.model_validate(data)


def test_nav_deducts_project_obligations_inside_projects_and_corporate_debt_once():
    result = value_nav(nav())
    expected = Decimal("0.8") * Decimal("0.9") * 800 + Decimal("0.5") * 500 + 40 - 150 - 10
    assert result.equity_value == expected
    assert [p.contribution for p in result.projects] == [Decimal("576.00"), Decimal("250.0")]


def test_nav_with_missing_project_data_is_unavailable_not_book_based():
    result = value_nav(nav(projects=[]))
    assert result.status == "unavailable" and result.reason == "project_data_missing" and result.per_share is None
    partial = nav()
    broken = value_nav(partial.model_copy(update={"projects": (partial.projects[0].model_copy(update={"gross_value": None}),)}))
    assert broken.status == "unavailable"


def test_cyclical_normalisation_uses_window_average_not_peak():
    history = [("2016", "2"), ("2017", "3"), ("2018", "10"), ("2019", "4"), ("2020", "1"), ("2021", "6"), ("2022", "2")]
    inputs = CyclicalInputs.model_validate({"eps_history": [{"year": y, "eps": e} for y, e in history], "window_years": 7,
                                            "reason": "Một chu kỳ giá thép đầy đủ 2016–2022", "cost_of_equity": "0.14", **APPROVED})
    result = value_cyclical(inputs)
    assert result.normalized_eps == Decimal(28) / 7
    assert result.per_share == (Decimal(28) / 7) / Decimal("0.14")


@pytest.mark.parametrize("changes", [{"window_years": 3}, {"reason": ""}])
def test_cyclical_window_needs_full_cycle_and_reason(changes):
    data = {"eps_history": [{"year": str(2016 + i), "eps": "1"} for i in range(7)], "window_years": 7,
            "reason": "x", "cost_of_equity": "0.14", **APPROVED}
    data.update(changes)
    with pytest.raises(ValidationError):
        CyclicalInputs.model_validate(data)


def test_cyclical_history_shorter_than_window_unavailable():
    inputs = CyclicalInputs.model_validate({"eps_history": [{"year": "2021", "eps": "1"}], "window_years": 7, "reason": "chu kỳ",
                                            "cost_of_equity": "0.14", **APPROVED})
    assert value_cyclical(inputs).status == "unavailable"


def test_unapproved_inputs_never_activate_zone():
    result = value_residual_income(ri(approved=False))
    assert result.status == "draft" and result.buy_zone_active is False


def econ(**changes):
    data = {"industry_tag": "other", "regulated_deposit_taker": False, "project_based_assets": False, "commodity_cyclical": False,
            "stable_dividend_capacity": False, "predictable_free_cash_flow": False}
    data.update(changes)
    return IssuerEconomics.model_validate(data)


@pytest.mark.parametrize("changes, model", [
    ({"regulated_deposit_taker": True}, "residual_income"),
    ({"project_based_assets": True}, "nav"),
    ({"commodity_cyclical": True}, "cyclical_normalized"),
    ({"stable_dividend_capacity": True}, "ddm"),
    ({"predictable_free_cash_flow": True}, "fcff_dcf"),
    ({}, None),
])
def test_selector_uses_economics(changes, model):
    assert select_model(econ(**changes)).primary == model


def test_industry_tag_alone_does_not_pick_a_model():
    choice = select_model(econ(industry_tag="bank"))
    assert choice.primary is None and choice.reason == "no_model_fits_economics"


def test_cross_check_lists_differences_and_never_averages():
    comps = [Comparable(entity_id="ent-a", multiple_name="P/B", multiple="1.2", source_id="doc-a", roe="0.18", growth="0.10", note="ROE cao hơn"),
             Comparable(entity_id="ent-b", multiple_name="P/B", multiple="0.9", source_id="doc-b", roe="0.11", growth="0.06", note="Tài sản yếu hơn")]
    check = cross_check(primary_model="residual_income", primary_per_share=Decimal(100), comparables=comps, subject_roe=Decimal("0.15"))
    assert [c.entity_id for c in check.rows] == ["ent-a", "ent-b"]
    assert check.rows[0].roe_gap == Decimal("0.03") and check.rows[0].source_id == "doc-a"
    assert not hasattr(check, "blended_value") and check.basis_note
