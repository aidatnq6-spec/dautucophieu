"""Dự phòng đi vào lợi nhuận (ngân hàng), Chất lượng tài sản ngân hàng part 3 (owner, 23/11/2026). Made-up figures."""

from investment_agent.domain.bank_figures import provision_view

B = 1_000_000_000


def st(expense=None, ppop=None, loans=None):
    out = {}
    for line, v in (("provision_expense", expense), ("ppop", ppop), ("loans_gross", loans)):
        if v is not None:
            out[line] = str(v * B)
    return out


def bad(g3, g4, g5):
    """A quarter of the asset quality table (tỷ đồng): only groups 3–5 matter here."""
    return {"group1": "1000", "group2": "10", "group3": str(g3), "group4": str(g4), "group5": str(g5)}


YEAR = {"2025-Q3": st(1000, 4000, 900_000), "2025-Q4": st(1100, 4200, 950_000), "2026-Q1": st(900, 4100, 960_000), "2026-Q2": st(800, 4300, 980_000),
        "2026-Q3": st(600, 4500, 1_000_000)}


def test_each_quarter_sets_the_provision_against_profit_before_it_and_the_latest_has_its_credit_cost():
    v = provision_view(YEAR, {})
    assert v["quarter"] == "2026-Q3" and v["share"] == "0.1333"  # 600 / 4.500
    assert [r["quarter"] for r in v["rows"]] == ["2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]
    assert v["rows"][0] == {"quarter": "2025-Q3", "expense": "1000", "ppop": "4000", "share": "0.2500"}
    assert v["credit_cost"] == "0.0036" and v["credit_cost_missing"] == []  # (1.100 + 900 + 800 + 600) / ((1.000.000 + 900.000) / 2)
    assert v["expense_growth_yoy"] == "-0.4000"


def test_credit_cost_needs_four_quarters_and_the_loans_of_a_year_before_and_names_what_is_missing():
    v = provision_view({k: q for k, q in YEAR.items() if k != "2026-Q1"}, {})
    assert v["credit_cost"] is None and v["credit_cost_missing"] == ["2026-Q1"]
    v = provision_view({**YEAR, "2025-Q3": st(1000, 4000)}, {})
    assert v["credit_cost"] is None and v["credit_cost_missing"] == ["2025-Q3"]  # no loans to average with


def test_a_cut_of_30_percent_on_a_year_while_bad_debt_grows_is_flagged():
    v = provision_view(YEAR, {"2026-Q2": bad(8, 8, 9), "2026-Q3": bad(10, 10, 7)})
    assert v["flag"] is True and v["bad_growth_qoq"] == "0.0800" and v["why_not"] is None  # 25 → 27
    assert provision_view(YEAR, {"2026-Q2": bad(10, 10, 7), "2026-Q3": bad(8, 8, 9)})["flag"] is False  # bad debt down
    assert provision_view({**YEAR, "2026-Q3": st(701, 4500, 1_000_000)}, {"2026-Q2": bad(8, 8, 9), "2026-Q3": bad(10, 10, 7)})["flag"] is False  # −29,9%


def test_without_groups_3_to_5_a_cut_raises_no_flag_and_says_why_and_a_year_ago_at_nil_is_no_base():
    v = provision_view(YEAR, {})
    assert v["flag"] is None and v["why_not"] == "Chưa có nợ nhóm 3–5 của 2026-Q3 và quý trước để xét."
    v = provision_view({**YEAR, "2025-Q3": st(0, 4000, 900_000)}, {"2026-Q2": bad(8, 8, 9), "2026-Q3": bad(10, 10, 7)})
    assert v["flag"] is None and v["expense_growth_yoy"] is None and v["why_not"] == "Cùng kỳ năm trước không có chi phí dự phòng dương để so."


def test_a_loss_before_provisions_gives_no_share_and_no_quarter_gives_an_empty_view():
    v = provision_view({"2026-Q3": st(600, -100)}, {})
    assert v["rows"][0]["share"] is None and v["share"] is None
    assert provision_view({"2026-Q3": {"npat_parent": str(B)}}, {}) == {
        "rows": [], "quarter": None, "share": None, "credit_cost": None, "credit_cost_missing": [], "expense_growth_yoy": None,
        "bad_growth_qoq": None, "bad_now": None, "bad_prev": None, "flag": None, "why_not": None}
