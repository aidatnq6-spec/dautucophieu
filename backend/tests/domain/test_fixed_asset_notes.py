from datetime import date

import pytest

from investment_agent.domain.fixed_asset_notes import NoteError, complete, due_view, postpone, validate_notes

B = 10**9


def project(**more):
    return {"name": " Dung Quất 2 ", "due": "Q3/2025", "read_period": "2024", "cip_value": "60.000", "budget": "85000",
            "source_url": "https://example.com/bctc.pdf", "note": "lò cao số 5", **more}


def test_a_project_keeps_its_due_quarter_figures_and_starts_open():
    projects, ranges = validate_notes([project()], {"machinery": {"from": "1", "to": "25"}, "period": "2021"}, stored=[])
    p = projects[0]
    assert {k: p[k] for k in ("name", "due", "read_period", "cip_value", "budget", "status", "done_on", "postpones")} == {
        "name": "Dung Quất 2", "due": "2025-Q3", "read_period": "2024", "cip_value": "60000", "budget": "85000", "status": "open", "done_on": None,
        "postpones": []}
    assert len(p["id"]) == 12
    assert ranges == {"period": "2021", "groups": {"machinery": {"from": 1, "to": 25}}}


def test_bad_notes_are_refused_with_a_reason():
    for raw, ranges, code in (([project(name="")], {}, "invalid_name"), ([project(due="")], {}, "invalid_quarter"), ([project(due="Q5/2025")], {}, "invalid_quarter"),
                              ([project(read_period="2025-13")], {}, "invalid_period"), ([project(budget="-1")], {}, "invalid_amount"),
                              ([project(source_url="ftp://x")], {}, "invalid_source"), ([project() for _ in range(21)], {}, "too_many"),
                              ([], {"machinery": {"from": "30", "to": "5"}}, "invalid_range"), ([], {"buildings": {"from": "1", "to": "101"}}, "invalid_range"),
                              ([], {"spaceships": {"from": "1", "to": "2"}}, "invalid_group")):
        with pytest.raises(NoteError) as err:
            validate_notes(raw, ranges, stored=[])
        assert err.value.code == code


def test_the_due_quarter_changes_only_through_a_postponement_and_status_stays_as_stored():
    stored, _ = validate_notes([project()], {}, stored=[])
    pid = stored[0]["id"]
    with pytest.raises(NoteError) as err:
        validate_notes([project(id=pid, due="Q4/2025")], {}, stored=stored)
    assert err.value.code == "due_locked"
    kept, _ = validate_notes([project(id=pid, name="DQ2", status="done", postpones=[{"x": 1}])], {}, stored=stored)  # status and history from the store
    assert kept[0]["name"] == "DQ2" and kept[0]["status"] == "open" and kept[0]["postpones"] == []
    later = postpone(stored, pid, "Q2/2026", " chậm lắp đặt ", today=date(2025, 11, 1))
    assert later[0]["due"] == "2026-Q2" and later[0]["postpones"] == [{"from": "2025-Q3", "to": "2026-Q2", "on": "2025-11-01", "reason": "chậm lắp đặt"}]
    for to, code in (("Q3/2025", "not_later"), ("Q1/2025", "not_later"), ("x", "invalid_quarter")):
        with pytest.raises(NoteError) as err:
            postpone(stored, pid, to, "", today=date(2025, 11, 1))
        assert err.value.code == code
    done = complete(later, pid, today=date(2026, 8, 1))
    assert done[0]["status"] == "done" and done[0]["done_on"] == "2026-08-01"
    with pytest.raises(NoteError) as err:
        postpone(done, pid, "Q4/2026", "", today=date(2026, 8, 2))
    assert err.value.code == "not_open"
    with pytest.raises(NoteError) as err:
        complete(stored, "nope", today=date(2026, 8, 1))
    assert err.value.code == "not_found"


def test_an_open_project_is_due_once_its_quarter_s_report_is_stored_with_the_company_s_figures():
    projects, _ = validate_notes([project(), project(name="Nhà máy B", due="Q1/2026", read_period="")], {}, stored=[])
    statements = {"years": {"2024": {"cip": str(63656 * B), "ppe_gross": str(108147 * B)}},
                  "quarters": {"2025-Q3": {"cip": str(15000 * B), "ppe_gross": str(170000 * B)}, "2025-Q4": {"cip": str(10721 * B), "ppe_gross": str(182309 * B)}}}
    view = due_view(projects, statements, today=date(2026, 4, 20))
    a, b = view
    assert a["state"] == "due" and a["at_read"] == {"period": "2024", "cip": str(63656 * B), "ppe_gross": str(108147 * B)}
    assert a["at_due"] == {"period": "2025-Q3", "cip": str(15000 * B), "ppe_gross": str(170000 * B)}
    assert a["latest"] == {"period": "2025-Q4", "cip": str(10721 * B), "ppe_gross": str(182309 * B)}
    assert b["state"] == "waiting_report" and b["at_due"] is None and b["at_read"] is None  # Q1/2026 over, its report not stored yet
    assert due_view(projects, {"years": statements["years"]}, today=date(2025, 8, 1))[0]["state"] == "upcoming"  # Q3/2025 not over
    assert due_view(complete(projects, a["id"], today=date(2026, 4, 21)), statements, today=date(2026, 4, 21))[0]["state"] == "done"


def test_the_yearly_allocation_of_prepaid_expenses_gives_the_years_left_at_that_pace_owner_25_11_2026():
    """HPG 2021: 425 tỷ allocated (109 tools, 139 overhauls among them) against 3.171 tỷ long-term prepaid: about 7,5 years at that pace."""
    from investment_agent.domain.fixed_asset_notes import prepaid_view, validate_prepaid
    kept = validate_prepaid({"2021": {"tools": "109", "overhaul": "139", "total": "425"}, "2022": {"tools": "100", "land": "50"}})
    assert kept == {"2021": {"tools": "109", "overhaul": "139", "total": "425"}, "2022": {"tools": "100", "land": "50"}}
    statements = {"years": {"2021": {"prepaid_lt": str(3171 * B), "pbt": str(37057 * B)}, "2022": {"prepaid_lt": str(3929 * B)}}}
    a, b = prepaid_view(kept, statements)
    assert a == {"year": "2021", "items": {"tools": "109", "overhaul": "139"}, "total": "425", "summed": False, "prepaid_lt": str(3171 * B),
                 "years_left": "7.5", "to_pbt": "0.0115"}
    assert b["total"] == "150" and b["summed"] is True and b["years_left"] == "26.2" and b["to_pbt"] is None  # no profit line that year
    for raw, code in (({"20x1": {"tools": "1"}}, "invalid_year"), ({"2021": {"ships": "1"}}, "invalid_kind"), ({"2021": {"tools": "-1"}}, "invalid_amount"),
                      ({"2021": {}}, "empty_year")):
        with pytest.raises(NoteError) as err:
            validate_prepaid(raw)
        assert err.value.code == code


def test_a_deal_gives_its_goodwill_by_the_lesson_s_formula_and_its_yearly_charge_owner_25_11_2026():
    """Bài lợi thế thương mại: goodwill = price − share × fair value of net assets; positive: an asset amortised over at most 10 years;
    negative: a bargain purchase, a one-off gain in that year."""
    from investment_agent.domain.fixed_asset_notes import deals_view, validate_deals
    kept = validate_deals([{"name": " Công ty B ", "date": "15/03/2024", "share": "60", "price": "1.000", "net_assets": "1000", "years": "10"},
                           {"name": "Công ty C", "date": "2025-06-30", "share": "100", "price": "300", "net_assets": "-50,5"},
                           {"name": "Công ty D", "date": "01/01/2025", "share": "51", "price": "100", "net_assets": "400"}])
    assert {k: kept[0][k] for k in ("name", "date", "share", "price", "net_assets", "years")} == {
        "name": "Công ty B", "date": "2024-03-15", "share": "60", "price": "1000", "net_assets": "1000", "years": 10}
    assert [d["name"] for d in kept] == ["Công ty B", "Công ty D", "Công ty C"]  # by the day bought
    assert kept[2]["net_assets"] == "-50.5" and kept[2]["years"] is None
    b, d, c = deals_view(kept, today=date(2026, 11, 25))
    assert b["goodwill"] == "400" and b["kind"] == "goodwill" and b["per_year"] == "40" and b["ends"] == "2034-03-15" and b["charging"] is True
    assert c["goodwill"] == "350.5" and c["kind"] == "goodwill" and c["per_year"] is None  # no years written: no schedule
    assert d["goodwill"] == "-104" and d["kind"] == "bargain" and d["gain_year"] == "2025" and d["per_year"] is None
    for raw, code in (([{"name": "", "date": "2024-01-01", "share": "60", "price": "1", "net_assets": "1"}], "invalid_name"),
                      ([{"name": "B", "date": "32/01/2024", "share": "60", "price": "1", "net_assets": "1"}], "invalid_date"),
                      ([{"name": "B", "date": "2024-01-01", "share": "0", "price": "1", "net_assets": "1"}], "invalid_share"),
                      ([{"name": "B", "date": "2024-01-01", "share": "101", "price": "1", "net_assets": "1"}], "invalid_share"),
                      ([{"name": "B", "date": "2024-01-01", "share": "60", "price": "", "net_assets": "1"}], "invalid_amount"),
                      ([{"name": "B", "date": "2024-01-01", "share": "60", "price": "1", "net_assets": "x"}], "invalid_amount"),
                      ([{"name": "B", "date": "2024-01-01", "share": "60", "price": "1", "net_assets": "1", "years": "11"}], "invalid_years")):
        with pytest.raises(NoteError) as err:
            validate_deals(raw)
        assert err.value.code == code


NVL_DEALS = [{"name": "Nova Final Solution", "date": "30/06/2021", "share": "99.98", "price": "5598", "net_assets": "7315", "note_goodwill": "-1670"},
             {"name": "Greenland", "date": "29/03/2021", "share": "69.87", "price": "2859", "net_assets": "3896", "note_goodwill": "103", "nci_part": "34",
              "years": "10"}]


def test_a_deal_shows_the_notes_goodwill_beside_the_formula_and_uses_the_notes_owner_25_11_2026():
    """Bài hợp nhất kinh doanh, NVL 2021: the formula gives −1.715,5 for Final Solution, the notes −1.670; Greenland 103 for the group, 34 for
    non-controlling interests."""
    from investment_agent.domain.fixed_asset_notes import deals_view, validate_deals
    green, final = deals_view(validate_deals(NVL_DEALS), today=date(2026, 11, 25))
    assert final["computed"] == "-1715.537" and final["note_goodwill"] == "-1670" and final["gap"] == "-45.537"
    assert final["goodwill"] == "-1670" and final["kind"] == "bargain" and final["gain_year"] == "2021"
    assert green["goodwill"] == "103" and green["nci_part"] == "34" and green["per_year"] == "10.3"
    with pytest.raises(NoteError) as err:
        validate_deals([{**NVL_DEALS[1], "nci_part": "-1"}])
    assert err.value.code == "invalid_amount"


def test_the_yearly_goodwill_movement_leaves_what_amortisation_does_not_explain_owner_25_11_2026():
    """NVL 2021: 5.950,8 at the start + 103 (Greenland) − 821 amortised (notes) = 5.232,8 against 5.104,0 at the end: 128,8 other decreases."""
    from investment_agent.domain.fixed_asset_notes import deals_view, goodwill_moves, validate_amort, validate_deals
    deals = deals_view(validate_deals(NVL_DEALS), today=date(2026, 11, 25))
    statements = {"years": {"2020": {"goodwill": str(int(5950.8 * 10) * 10**8)}, "2021": {"goodwill": str(5104 * B), "admin": str(int(1325.6 * 10) * 10**8),
                                                                                          "pbt": str(int(5086.2 * 10) * 10**8)},
                            "2022": {"goodwill": str(int(4544.3 * 10) * 10**8)}}}
    amort = validate_amort({"2021": "821"})
    assert amort == {"2021": "821"}
    moves = {m["year"]: m for m in goodwill_moves(deals, amort, statements)}
    m = moves["2021"]
    assert (m["opening"], m["added"], m["amortised"], m["closing"], m["other"]) == ("5950.8", "103", "821", "5104", "128.8")
    assert m["decline"] == "949.8" and m["to_admin"] == "0.6193" and m["to_pbt"] == "0.1614"
    assert moves["2022"]["amortised"] is None and moves["2022"]["other"] is None and moves["2022"]["decline"] == "559.7"
    assert "2020" not in moves  # no year before it
    with pytest.raises(NoteError) as err:
        validate_amort({"2021": "-5"})
    assert err.value.code == "invalid_amount"


def test_a_bargain_gain_from_a_tenth_of_profit_before_tax_is_a_sign_with_profit_without_it_owner_25_11_2026():
    """NVL 2021: 1.670 of 5.086,2 tỷ = 32,8%; without it 3.416,2 tỷ."""
    from investment_agent.domain.fixed_asset_notes import bargain_years, deals_view, validate_deals
    deals = deals_view(validate_deals(NVL_DEALS), today=date(2026, 11, 25))
    (y,) = bargain_years(deals, {"years": {"2021": {"pbt": str(int(5086.2 * 10) * 10**8)}}})
    assert y == {"year": "2021", "gain": "1670", "deals": ["Nova Final Solution"], "pbt": "5086.2", "share": "0.3283", "pbt_without": "3416.2", "flag": True}
    (small,) = bargain_years(deals, {"years": {"2021": {"pbt": str(20000 * B)}}})
    assert small["share"] == "0.0835" and small["flag"] is False
    (loss,) = bargain_years(deals, {"years": {"2021": {"pbt": str(-100 * B)}}})
    assert loss["share"] is None and loss["flag"] is True  # a loss before tax with a bargain gain: always
    (unknown,) = bargain_years(deals, {"years": {}})
    assert unknown["pbt"] is None and unknown["flag"] is None


HPG_LOANS = [{"lender": "Các ngân hàng (ngắn hạn, VND)", "currency": "VND", "term": "short", "balance": "12998", "rate_from": "2,4", "rate_to": "6,5"},
             {"lender": "Các ngân hàng (ngắn hạn, USD)", "currency": "USD", "term": "short", "balance": "6357", "rate_from": "1,2", "rate_to": "2,3"},
             {"lender": "HSBC", "currency": "VND", "term": "long", "balance": "503", "maturity": "2024", "collateral": "Máy móc dây chuyền Thép Hải Dương"},
             {"lender": "Ngân hàng X", "currency": "USD", "term": "long", "balance": "1000", "maturity": "2025", "base": "Libor", "margin": "2,05"}]


def test_loans_from_the_notes_give_currency_mix_maturities_rates_and_a_check_against_the_balance_sheet_owner_25_11_2026():
    """Bài nợ vay, HPG 2021 (thuyết minh 24): VND 12.998 at 2,4–6,5%, USD 6.357 at 1,2–2,3%; HSBC 503 due 2024; 6.200 long-term due within a year."""
    from investment_agent.domain.fixed_asset_notes import debt_view, validate_debt_notes, validate_loans
    loans = validate_loans(HPG_LOANS)
    assert loans[0]["rate_from"] == "2.4" and loans[2]["maturity"] == "2024" and loans[3]["margin"] == "2.05" and loans[3]["base"] == "Libor"
    notes = validate_debt_notes({"period": "2021", "current_portion": "6200", "fx_shock": "5"})
    assert notes == {"period": "2021", "current_portion": "6200", "fx_shock": "5"}
    statements = {"years": {"2021": {"st_debt": str(int(43747.6 * 10) * 10**8), "lt_debt": str(int(13464.9 * 10) * 10**8), "pbt": str(37057 * B)}}}
    v = debt_view(loans, notes, statements)
    assert v["total"] == "20858" and v["by_currency"] == {"USD": "7357", "VND": "13501"} and v["by_term"] == {"long": "1503", "short": "19355"}
    assert v["rates"] == {"USD": {"from": "1.2", "to": "2.3", "floating": ["Libor + 2,05%"]}, "VND": {"from": "2.4", "to": "6.5", "floating": []}}
    assert v["maturities"] == {"2024": "503", "2025": "1000", "none": "19355"}
    assert v["reported"] == "57212.5" and v["covered"] == "0.3646"  # what the owner wrote against the balance sheet's borrowings
    assert v["foreign"] == "7357" and v["fx_loss"] == "367.85" and v["fx_to_pbt"] == "0.0099"  # 7.357 × 5%, against 37.057
    assert v["current_portion"] == "6200"
    for raw, code in (([{**HPG_LOANS[0], "lender": ""}], "invalid_name"), ([{**HPG_LOANS[0], "currency": "BTC"}], "invalid_currency"),
                      ([{**HPG_LOANS[0], "term": "mid"}], "invalid_term"), ([{**HPG_LOANS[0], "balance": ""}], "invalid_amount"),
                      ([{**HPG_LOANS[0], "rate_from": "7", "rate_to": "6"}], "invalid_rate"), ([{**HPG_LOANS[0], "rate_to": "120"}], "invalid_rate"),
                      ([{**HPG_LOANS[2], "maturity": "20x4"}], "invalid_year")):
        with pytest.raises(NoteError) as err:
            validate_loans(raw)
        assert err.value.code == code
    with pytest.raises(NoteError) as err:
        validate_debt_notes({"period": "2021", "fx_shock": "250"})
    assert err.value.code == "invalid_shock"


def test_without_a_period_or_a_shock_the_check_and_scenario_stay_blank():
    from investment_agent.domain.fixed_asset_notes import debt_view, validate_debt_notes, validate_loans
    v = debt_view(validate_loans(HPG_LOANS[:1]), validate_debt_notes({}), {"years": {}})
    assert v["reported"] is None and v["covered"] is None and v["fx_loss"] is None and v["foreign"] == "0"


def test_segments_from_the_notes_give_each_segment_s_gross_profit_margin_and_share_and_a_check_owner_25_11_2026():
    """Bài doanh thu, giá vốn (HPG 2021, thuyết minh 31, 32): steel 149.000 revenue, 107.000 cost; the rest small; total 149.680 / 108.571."""
    from investment_agent.domain.fixed_asset_notes import segments_view, validate_segments
    kept = validate_segments({"2021": [{"name": " Thép, hàng hóa ", "revenue": "149.000", "cogs": "107000"}, {"name": "Dịch vụ, BĐS, cho thuê đất", "revenue": "680", "cogs": "1571"}]})
    assert kept == {"2021": [{"name": "Thép, hàng hóa", "revenue": "149000", "cogs": "107000"}, {"name": "Dịch vụ, BĐS, cho thuê đất", "revenue": "680", "cogs": "1571"}]}
    statements = {"years": {"2021": {"revenue": str(149680 * B), "cogs": str(108571 * B)}}}
    (v,) = segments_view(kept, statements)
    steel, other = v["rows"]
    assert (steel["gross"], steel["margin"], steel["share"]) == ("42000", "0.2819", "1.0217")
    assert (other["gross"], other["margin"], other["share"]) == ("-891", "-1.3103", "-0.0217")
    assert (v["revenue"], v["cogs"], v["gross"], v["margin"]) == ("149680", "108571", "41109", "0.2746")
    assert (v["reported_revenue"], v["reported_cogs"], v["revenue_gap"], v["cogs_gap"]) == ("149680", "108571", "0", "0")
    for raw, code in (({"20x1": [{"name": "A", "revenue": "1", "cogs": "1"}]}, "invalid_period"), ({"2021": [{"name": "", "revenue": "1", "cogs": "1"}]}, "invalid_name"),
                      ({"2021": [{"name": "A", "revenue": "", "cogs": "1"}]}, "invalid_amount"), ({"2021": []}, "empty_year"),
                      ({"2021": [{"name": str(i), "revenue": "1", "cogs": "1"} for i in range(13)]}, "too_many")):
        with pytest.raises(NoteError) as err:
            validate_segments(raw)
        assert err.value.code == code
    (blank,) = segments_view(kept, {"years": {}})
    assert blank["reported_revenue"] is None and blank["revenue_gap"] is None
