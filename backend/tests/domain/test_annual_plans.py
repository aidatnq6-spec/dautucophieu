from investment_agent.domain.annual_plans import plan_progress

B = 10**9
QUARTERS = {"2026-Q1": {"revenue": str(52901 * B), "npat": str(9000 * B), "npat_parent": str(8994 * B), "pbt": str(10762 * B)},
            "2026-Q2": {"revenue": str(55159 * B), "npat": str(6400 * B), "npat_parent": str(6371 * B), "pbt": str(7185 * B)},
            "2026-Q3": {"revenue": str(62214 * B), "npat": str(8265 * B), "npat_parent": str(8217 * B), "pbt": str(9109 * B)},
            "2025-Q1": {"revenue": str(37622 * B), "npat": str(3400 * B)}, "2025-Q2": {"revenue": str(35911 * B)},
            "2025-Q3": {"revenue": str(36407 * B), "npat": str(4000 * B)}, "2025-Q4": {"revenue": str(46176 * B), "npat": str(3900 * B)}}


def test_year_to_date_revenue_and_profit_against_the_plan_from_the_first_quarter_on():
    plans = {"2026": {"revenue": "210000", "profit": "22000", "profit_kind": "npat", "source": "Nghị quyết ĐHCĐ 2026"}}
    [p] = plan_progress(plans, QUARTERS)
    assert p["year"] == "2026" and p["through"] == "2026-Q3" and p["source"] == "Nghị quyết ĐHCĐ 2026"
    assert p["revenue"] == {"actual": str(170274 * B), "plan": str(210000 * B), "ratio": "0.8108", "reason": None}
    assert p["profit"] == {"actual": str(23665 * B), "plan": str(22000 * B), "ratio": "1.0757", "reason": None}


def test_the_profit_line_follows_the_kind_the_plan_names():
    [p] = plan_progress({"2026": {"profit": "30000", "profit_kind": "pbt", "source": "x"}}, QUARTERS)
    assert p["profit"]["actual"] == str(27056 * B) and p["revenue"] is None
    [p] = plan_progress({"2026": {"profit": "22000", "profit_kind": "npat_parent", "source": "x"}}, QUARTERS)
    assert p["profit"]["actual"] == str(23582 * B)


def test_a_missing_quarter_stops_the_sum_and_says_which():
    [p] = plan_progress({"2025": {"revenue": "150000", "profit": "15000", "profit_kind": "npat", "source": "x"}}, QUARTERS)
    assert p["through"] == "2025-Q4" and p["revenue"]["ratio"] == "1.0408"  # 156,116 / 150,000
    assert p["profit"] == {"actual": str(3400 * B), "plan": str(15000 * B), "ratio": "0.2267", "reason": "Thiếu LNST quý 2/2025: chỉ cộng tới quý 1"}


def test_a_year_without_any_quarter_yet_and_newest_years_first():
    out = plan_progress({"2027": {"revenue": "1", "source": "x"}, "2026": {"revenue": "210000", "source": "x"}}, QUARTERS)
    assert [p["year"] for p in out] == ["2027", "2026"]
    assert out[0]["through"] is None and out[0]["revenue"] == {"actual": None, "plan": str(B), "ratio": None, "reason": "Chưa có số quý 1/2027"}
    assert plan_progress({"2026": {"revenue": "1", "source": "x"}}, None)[0]["revenue"]["reason"] == "Chưa có số quý VNDirect của mã này"
