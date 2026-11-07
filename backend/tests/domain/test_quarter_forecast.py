from investment_agent.domain.quarter_forecast import forecast_quarter, next_quarter

B = 10**9
QUARTERS = {"2025-Q4": {"revenue": str(46176 * B), "npat_parent": str(3864 * B), "ebitda_base": "x"}, "2026-Q3": {"revenue": str(62214 * B)}}
FULL = {"revenue_yoy": "0.55", "gross_margin": "0.18", "selling_pct": "0.025", "admin_pct": "0.0075", "fin_income": "900", "fin_expense": "1430",
        "interest": "1430", "associates": "0", "other_profit": "0", "tax_rate": "0.14", "minority_pct": "0.006", "depreciation": "3100"}


def test_the_next_quarter_follows_the_latest_reported_one():
    assert next_quarter(QUARTERS) == "2026-Q4" and next_quarter({"2026-Q4": {}}) == "2027-Q1" and next_quarter({}) is None


def test_the_owner_s_assumptions_give_the_quarter_line_by_line_from_the_same_quarter_a_year_before():
    out = forecast_quarter(QUARTERS, "2026-Q4", FULL)
    v = out["values"]
    assert out["base"] == "2025-Q4" and out["reason"] is None
    assert v["revenue"] == "71572800000000"  # 46,176 × 1.55 = 71,572.8 tỷ
    assert v["revenue_yoy"] == "0.5500" and v["cogs"] == "-58689696000000" and v["gross_profit"] == "12883104000000"
    assert v["gross_margin"] == "0.1800" and v["selling"] == "-1789320000000" and v["admin"] == "-536796000000"
    assert v["core_profit"] == "10556988000000"  # gross − selling − admin
    assert v["pbt"] == "10026988000000"  # core + 900 − 1,430 + 0 + 0
    assert v["npat_parent"] == "8571470421920"  # pbt × (1 − 14 %) × (1 − 0.6 %)
    assert v["npat_parent_yoy"] == "1.2183"  # against 3,864 tỷ
    assert v["ebit"] == "11456988000000" and v["ebitda"] == "14556988000000" and v["interest"] == "-1430000000000"


def test_a_blank_assumption_leaves_what_rests_on_it_blank():
    partial = {"revenue_yoy": "0.10", "gross_margin": "0.20"}
    v = forecast_quarter(QUARTERS, "2026-Q4", partial)["values"]
    assert v["revenue"] is not None and v["gross_profit"] is not None
    assert v["core_profit"] is None and v["pbt"] is None and v["npat_parent"] is None and v["ebitda"] is None


def test_without_the_same_quarter_a_year_before_there_is_no_forecast():
    out = forecast_quarter(QUARTERS, "2027-Q1", FULL)
    assert out["values"] == {} and out["reason"] == "Chưa có doanh thu Q1/2026 để làm gốc so cùng kỳ"
