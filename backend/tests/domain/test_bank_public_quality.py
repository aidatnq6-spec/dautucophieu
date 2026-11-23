"""Chất lượng tài sản ngân hàng (owner, 23/11/2026), part 2: the table runs on public figures too, the owner's entries on top."""

from investment_agent.domain.bank_figures import merged_quarters, public_quarters, quality_trend

B = 1_000_000_000  # đồng in one tỷ


def notes(g1, g2, g3, g4, g5, loans=None):
    """A quarter of Vietcap's notes in whole đồng; `loans` the total it prints (the groups' sum unless given)."""
    groups = [g * B for g in (g1, g2, g3, g4, g5)]
    out = {f"group{i}": str(v) for i, v in enumerate(groups, 1)}
    out["loans"] = str((loans if loans is not None else g1 + g2 + g3 + g4 + g5) * B)
    return out


def statement(loans=None, reserve=None, accrued=None):
    """A quarter of VNDirect's bank lines in đồng; the reserve negative as the source gives it."""
    out = {}
    for line, v in (("loans_gross", loans), ("loan_reserve", None if reserve is None else -reserve), ("accrued_interest", accrued)):
        if v is not None:
            out[line] = str(v * B)
    return out


def test_vietcap_groups_and_vndirect_reserve_and_accrued_interest_make_a_quarter_in_ty_dong_each_with_its_source():
    out = public_quarters({"2026-09-30": notes(1200, 17, 10, 10, 7)}, {"2026-Q3": statement(loans=1244, reserve=22.5, accrued=70)}, [])
    q = out["2026-Q3"]
    assert q["values"] == {"group1": "1200", "group2": "17", "group3": "10", "group4": "10", "group5": "7", "reserve": "22.5", "accrued_interest": "70"}
    assert q["sources"] == {**{f"group{i}": "Vietcap" for i in range(1, 6)}, "reserve": "VNDirect", "accrued_interest": "VNDirect"}
    assert q["notes"] == []


def test_groups_that_do_not_add_up_to_vietcaps_total_are_left_blank_and_said_so():
    out = public_quarters({"2026-09-30": notes(1200, 17, 10, 10, 7, loans=1300)}, {"2026-Q3": statement(reserve=20)}, [])
    q = out["2026-Q3"]
    assert "group1" not in q["values"] and q["values"] == {"reserve": "20"}
    assert q["notes"] == ["Nợ nhóm 1–5 trên Vietcap cộng ra 1.244 tỷ, khác tổng dư nợ 1.300 tỷ Vietcap ghi: để trống."]


def test_groups_far_from_vndirects_loans_keep_both_figures_without_choosing():
    q = public_quarters({"2026-09-30": notes(1200, 17, 10, 10, 7)}, {"2026-Q3": statement(loans=1300)}, [])["2026-Q3"]
    assert q["values"]["group1"] == "1200"
    assert q["notes"] == ["Tổng nợ nhóm 1–5 (Vietcap, 1.244 tỷ) lệch 4,3% so với cho vay khách hàng (VNDirect, 1.300 tỷ): ghi cả hai, không chọn bên nào."]
    assert public_quarters({"2026-09-30": notes(1200, 17, 10, 10, 7)}, {"2026-Q3": statement(loans=1250)}, [])["2026-Q3"]["notes"] == []  # 0,5%: within 1%


def test_a_balance_vndirect_gives_as_zero_is_said_to_be_missing():
    q = public_quarters({}, {"2008-Q1": statement(loans=7216)}, [{"period": "2008-Q1", "line": "accrued_interest"},
                                                                 {"period": "2008-Q1", "line": "loan_reserve"}, {"period": "2007", "line": "loan_reserve"}])
    assert q == {"2008-Q1": {"values": {}, "sources": {}, "notes": [
        "VNDirect ghi 0 cho dự phòng rủi ro cho vay khách hàng, lãi và phí phải thu: coi là chưa có số."]}}


def test_a_statement_quarter_without_any_of_these_lines_makes_no_quarter():
    """The store holds profit and equity for every quarter; a quarter with none of these figures and nothing to say is no quarter here."""
    assert public_quarters({}, {"2026-Q4": {"npat_parent": str(B), "ppop": str(2 * B)}, "2026-Q3": statement(accrued=70)}, []) == {
        "2026-Q3": {"values": {"accrued_interest": "70"}, "sources": {"accrued_interest": "VNDirect"}, "notes": []}}


def test_the_owners_entry_wins_field_by_field_and_a_quarter_only_entered_is_kept():
    public = public_quarters({"2026-09-30": notes(1200, 17, 10, 10, 7)}, {"2026-Q3": statement(reserve=22.5, accrued=70)}, [])
    entered = {"2026-Q3": {"group1": None, "reserve": "23", "real_estate_loans": "180", "car": None},
               "2026-Q2": {"group1": "1100", "group2": "10", "group3": "8", "group4": "8", "group5": "9", "reserve": "23.25", "accrued_interest": "50"}}
    out = merged_quarters(entered, public)
    assert out["2026-Q3"]["values"]["reserve"] == "23" and out["2026-Q3"]["sources"]["reserve"] == "số nhập tay"
    assert out["2026-Q3"]["values"]["group1"] == "1200" and out["2026-Q3"]["sources"]["group1"] == "Vietcap"  # an empty entry is no entry
    assert out["2026-Q3"]["sources"]["real_estate_loans"] == "số nhập tay" and "car" not in out["2026-Q3"]["values"]
    assert set(out["2026-Q2"]["sources"].values()) == {"số nhập tay"}
    t = quality_trend({k: v["values"] for k, v in out.items()})["2026-Q3"]
    assert "accrued_jump" in t["flags"]  # 50 entered → 70 public: +40%, with nothing entered for the latest quarter's accrued interest


def test_the_public_figures_alone_raise_the_signs():
    """Made-up figures: bad debt up while the reserve falls, accrued interest up 25%: the signs without a single entry."""
    public = public_quarters({"2026-06-30": notes(1100, 10, 8, 8, 9), "2026-09-30": notes(1200, 17, 10, 10, 7)},
                             {"2026-Q2": statement(reserve=24, accrued=56), "2026-Q3": statement(reserve=22.5, accrued=70)}, [])
    t = quality_trend({k: v["values"] for k, v in merged_quarters({}, public).items()})["2026-Q3"]
    assert {"group2_jump", "reserve_lagging", "accrued_jump"} <= set(t["flags"])
