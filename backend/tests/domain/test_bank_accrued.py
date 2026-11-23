"""Lãi dự thu so với thu nhập lãi, Chất lượng tài sản ngân hàng part 4 (owner, 23/11/2026). Made-up figures."""

from investment_agent.domain.bank_figures import accrued_view

B = 1_000_000_000


def income(v):
    return {"interest_income": str(v * B)}


def accrued(v):
    return {"accrued_interest": str(v)}  # the asset quality table, tỷ đồng


def test_accrued_interest_against_the_quarters_interest_income_beside_a_year_before_and_the_sign_from_20_points():
    v = accrued_view({"2025-Q3": income(1000), "2026-Q3": income(1100)}, {"2025-Q3": accrued(500), "2026-Q3": accrued(700)})
    assert v["quarter"] == "2026-Q3" and v["ratio"] == "0.6364" and v["ratio_year_ago"] == "0.5000"  # 700 / 1.100 ; 500 / 1.000
    assert v["accrued_growth_yoy"] == "0.4000" and v["income_growth_yoy"] == "0.1000" and v["flag"] is True and v["why_not"] is None
    v = accrued_view({"2025-Q3": income(1000), "2026-Q3": income(1100)}, {"2025-Q3": accrued(500), "2026-Q3": accrued(649)})
    assert v["flag"] is False  # 29,8% against 10%: 19,8 points


def test_the_latest_quarter_is_the_last_with_both_figures_and_a_missing_year_before_says_why():
    v = accrued_view({"2026-Q3": income(1100), "2026-Q4": income(1200)}, {"2026-Q3": accrued(700)})
    assert v["quarter"] == "2026-Q3" and v["ratio_year_ago"] is None and v["flag"] is None
    assert v["why_not"] == "Chưa có lãi dự thu và thu nhập lãi của 2025-Q3 để so cùng kỳ."
    assert accrued_view({}, {"2026-Q3": accrued(700)}) == {"quarter": None, "ratio": None, "ratio_year_ago": None, "accrued_growth_yoy": None,
                                                           "income_growth_yoy": None, "flag": None, "why_not": None}
