from investment_agent.domain.bank_figures import FIELDS, derive, parse_report_pages, quality_trend


def q(g1, g2, g3, g4, g5, reserve=None, accrued=None, real_estate=None, docs=None):
    return {"group1": str(g1), "group2": str(g2), "group3": str(g3), "group4": str(g4), "group5": str(g5), "reserve": None if reserve is None else str(reserve),
            "accrued_interest": None if accrued is None else str(accrued), "real_estate_loans": None if real_estate is None else str(real_estate),
            "discounted_documents": None if docs is None else str(docs)}


# Made-up figures shaped like the case in the owner's video: cover falling, group 2 up 70%, provisions written off, accrued interest and property loans racing ahead.
QUARTERS = {"2025-Q3": q(1000, 8, 5, 5, 10, reserve=20, accrued=50, real_estate=100, docs=8),
            "2025-Q4": q(1050, 9, 6, 6, 10, reserve=22, accrued=48, real_estate=110, docs=9),
            "2026-Q2": q(1150, 10, 8, 8, 9, reserve=23.25, accrued=50, real_estate=140, docs=10),
            "2026-Q3": q(1250, 17, 10, 10, 7, reserve=22.85, accrued=70, real_estate=180, docs=13)}


def test_the_new_figures_are_entered_like_the_others():
    assert {"reserve", "accrued_interest", "real_estate_loans", "discounted_documents"} <= set(FIELDS)


def test_cover_is_provisions_over_bad_debt_and_property_has_its_share_of_loans():
    d = derive(QUARTERS["2026-Q3"])
    assert d["llr"] == "0.8463" and d["real_estate_share"] == "0.1391"  # 22,85 / 27 ; 180 / 1.294
    assert derive(q(1, 0, 0, 0, 0, reserve=5))["llr"] is None  # no bad debt: no cover to state


def test_the_latest_quarter_is_set_against_the_last_one_a_year_before_and_the_start_of_the_year():
    t = quality_trend(QUARTERS)["2026-Q3"]
    assert (t["llr_prev"], t["llr_year_ago"], t["llr_start"]) == ("0.9300", "1.0000", "1.0000")
    assert (t["group2_growth_qoq"], t["loans_growth_qoq"], t["loans_growth_ytd"]) == ("0.7000", "0.0920", "0.1970")
    assert (t["accrued_growth_qoq"], t["real_estate_growth_ytd"], t["documents_growth_qoq"]) == ("0.4000", "0.6364", "0.3000")


def test_warning_signs_are_named():
    assert set(quality_trend(QUARTERS)["2026-Q3"]["flags"]) == {"llr_falling", "group2_jump", "reserve_lagging", "write_off", "accrued_jump", "real_estate_fast", "documents_jump"}


def test_a_calm_quarter_raises_nothing_and_a_missing_figure_is_not_guessed():
    calm = {"2026-Q2": q(1000, 10, 5, 5, 5, reserve=15, accrued=50, real_estate=100), "2026-Q3": q(1030, 10, 5, 5, 5, reserve=15.5, accrued=51, real_estate=102)}
    assert quality_trend(calm)["2026-Q3"]["flags"] == []
    gaps = {"2026-Q2": q(1000, 10, 5, 5, 5), "2026-Q3": q(1030, 20, 5, 5, 5)}
    t = quality_trend(gaps)["2026-Q3"]
    assert t["llr"] is None and t["llr_prev"] is None and t["accrued_growth_qoq"] is None and t["flags"] == ["group2_jump"]


def test_the_first_quarter_has_nothing_to_compare_with():
    t = quality_trend(QUARTERS)["2025-Q3"]
    assert t["llr_prev"] is None and t["group2_growth_qoq"] is None and t["flags"] == []


def test_provisions_and_accrued_interest_are_read_from_the_balance_sheet_as_positive_amounts():
    page = "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT\nĐơn vị: triệu đồng\nCho vay khách hàng 1.269.000.000\nDự phòng rủi ro cho vay khách hàng 9 (22.850.000)\nCác khoản lãi, phí phải thu 70.123.000\n"
    out = parse_report_pages([page])
    assert out["fields"]["reserve"] == {"value": "22850", "page": 1}
    assert out["fields"]["accrued_interest"] == {"value": "70123", "page": 1}
    assert "real_estate_loans" not in out["fields"] and "real_estate_loans" not in out["missing"]  # entered by hand only
