from investment_agent.domain.profit_bridge import profit_bridge

B = 10**9


def q(revenue, gross, selling, admin, fin_in, fin_out, assoc, other, tax, minority):
    pbt = gross + fin_in - fin_out + assoc - selling - admin + other
    npat = pbt - tax
    return {k: str(v * B) for k, v in {"revenue": revenue, "gross_profit": gross, "selling": selling, "admin": admin, "fin_income": fin_in,
                                       "fin_expense": fin_out, "associates": assoc, "other_profit": other, "pbt": pbt, "tax": tax, "npat": npat,
                                       "minority_profit": minority, "npat_parent": npat - minority}.items()}


QUARTERS = {"2025-Q3": q(1000, 400, 100, 80, 30, 20, 5, 5, 48, 12), "2026-Q3": q(1200, 420, 110, 90, 40, 30, 10, 0, 48, 2)}


def test_parent_profit_moves_from_last_year_s_quarter_to_this_one_line_by_line_with_nothing_left_over():
    out = profit_bridge(QUARTERS, "2026-Q3")
    assert out["status"] == "ok" and out["base_quarter"] == "2025-Q3"
    assert out["start"] == str(180 * B) and out["end"] == str(190 * B)
    steps = {s["id"]: s["amount"] for s in out["steps"]}
    # gross 400 → 420: revenue +200 at last year's 40% margin = +80; margin 35% vs 40% on 1,200 = −60
    assert steps == {"revenue": str(80 * B), "margin": str(-60 * B), "selling": str(-10 * B), "admin": str(-10 * B), "financial": "0",
                     "associates": str(5 * B), "other_profit": str(-5 * B), "tax": "0", "minority": str(10 * B)}
    assert out["other"] == "0"


def test_a_gap_no_line_explains_is_shown_on_its_own():
    quarters = {k: dict(v) for k, v in QUARTERS.items()}
    quarters["2026-Q3"]["npat_parent"] = str(193 * B)
    out = profit_bridge(quarters, "2026-Q3")
    assert out["other"] == str(3 * B)


def test_a_quarter_without_the_lines_or_last_year_says_so():
    assert profit_bridge(QUARTERS, "2025-Q3")["status"] == "no_base"
    assert profit_bridge({"2025-Q3": {"npat_parent": "1"}, "2026-Q3": {"npat_parent": "2"}}, "2026-Q3") == {
        "status": "missing_lines", "quarter": "2026-Q3", "missing": ["revenue", "gross_profit"]}
