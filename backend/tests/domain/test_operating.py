from investment_agent.domain.operating import group_view, valid_period

GROUP = {"name": "Sản lượng bán", "unit": "nghìn tấn", "period": "quarter", "series": ["Thép XD", "HRC"], "chart": "stack",
         "values": {"2026-Q3": {"Thép XD": "1340", "HRC": "2100"}, "2025-Q3": {"Thép XD": "1060", "HRC": "1270"}, "2026-Q2": {"Thép XD": "1300"}},
         "sources": {"2026-Q3": "Bản tin SXKD HPG 10/2026", "2025-Q3": "Bản tin 10/2025", "2026-Q2": "Bản tin 07/2026"}}


def test_periods_follow_the_group_s_kind():
    assert valid_period("2026-Q3", "quarter") and valid_period("2026-09", "month") and valid_period("2026", "year")
    assert not valid_period("2026-13", "month") and not valid_period("2026-Q5", "quarter") and not valid_period("2026-Q3", "month")


def test_each_period_has_its_values_total_shares_and_growth_against_a_year_before():
    v = group_view("san-luong", GROUP)
    assert v["periods"] == ["2025-Q3", "2026-Q2", "2026-Q3"]
    q3 = v["rows"][-1]
    assert q3 == {"period": "2026-Q3", "values": {"Thép XD": "1340", "HRC": "2100"}, "total": "3440", "shares": {"Thép XD": "0.3895", "HRC": "0.6105"},
                  "total_yoy": "0.4764", "source": "Bản tin SXKD HPG 10/2026", "missing": []}  # 3,440 against 2,330
    q2 = v["rows"][1]
    assert q2["total"] is None and q2["missing"] == ["HRC"] and q2["shares"] == {} and q2["total_yoy"] is None  # a missing line: no total


def test_lines_without_a_total_are_not_added_up():
    share = {**GROUP, "chart": "line", "unit": "%", "values": {"2026": {"Thép XD": "36", "HRC": "64"}}, "period": "year", "sources": {"2026": "VSA"}}
    row = group_view("thi-phan", share)["rows"][0]
    assert row["total"] is None and row["shares"] == {} and row["missing"] == []
