from investment_agent.market.bank_notes import bank_ratio_rows
from investment_agent.valuation.quality import report_quality

BN = 1_000_000_000


def year(revenue, gross, profit, assets, current_assets, current_liabilities, long_liabilities, receivables, cfo):
    return {k: str(v * BN) for k, v in dict(revenue=revenue, gross_profit=gross, profit=profit, total_assets=assets, current_assets=current_assets,
                                             current_liabilities=current_liabilities, long_liabilities=long_liabilities, receivables=receivables,
                                             cfo=cfo).items()}


# Improving every year: all nine criteria pass.
STRONG = {"annual": {"2023": year(80, 16, 4, 100, 50, 40, 30, 10, 5), "2024": year(90, 19, 6, 100, 55, 40, 28, 11, 8),
                     "2025": year(110, 25, 9, 105, 60, 38, 25, 12, 12)},
          "share_issues": [{"date": "2025-06-01", "kind": "bonus"}]}


def test_all_nine_criteria_pass_for_a_company_improving_on_every_line():
    q = report_quality(STRONG, "Công nghệ Thông tin")
    f = q["f_score"]
    assert f["year"] == "2025" and f["score"] == 9 and f["evaluated"] == 9 and f["level"] == "strong"
    assert [c["passed"] for c in f["criteria"]] == [True] * 9
    assert f["criteria"][0]["detail"] == "ROA 9,0% (lợi nhuận 9 tỷ / tài sản đầu kỳ 100 tỷ)"
    assert f["criteria"][6]["detail"] == "Không có đợt huy động vốn bằng cổ phiếu năm 2025 (cổ phiếu thưởng, cổ tức bằng cổ phiếu không tính)"
    assert [s["flag"] for s in q["signs"]] == [False, False, False, None, None, None, None]  # financial income and its cash, other receivables,
    # prepayments: not kept


def test_a_capital_raise_and_worse_lines_fail_and_the_signs_show_their_numbers():
    weak = {"annual": {"2023": year(100, 30, 8, 100, 60, 30, 10, 10, -2), "2024": year(100, 28, 7, 110, 60, 35, 15, 14, -3),
                       "2025": year(100, 25, 5, 120, 55, 40, 20, 20, -4)},
            "share_issues": [{"date": "2025-12-08", "kind": "raise"}]}
    q = report_quality(weak, "Bất động sản")
    f = q["f_score"]
    assert f["score"] == 1 and f["level"] == "weak"  # only ROA > 0
    assert f["criteria"][6]["passed"] is False and "Có đợt huy động vốn bằng cổ phiếu năm 2025" in f["criteria"][6]["detail"]
    signs = {s["id"]: s for s in q["signs"]}
    assert signs["profit_without_cash"]["flag"] is True
    assert signs["profit_without_cash"]["detail"] == "2023: lãi 8 tỷ, dòng tiền KD −2 tỷ · 2024: lãi 7 tỷ, dòng tiền KD −3 tỷ · 2025: lãi 5 tỷ, dòng tiền KD −4 tỷ"
    assert signs["receivables_outpace_revenue"]["flag"] is True  # receivables +42,9%, revenue 0%
    assert signs["accruals"]["flag"] is True  # (8+2)+(7+3)+(5+4) = 29 tỷ = 24,2% of 120 tỷ


def test_missing_lines_leave_criteria_unevaluated_and_no_level_below_seven():
    partial = {"annual": {"2024": {"profit": str(5 * BN), "total_assets": str(100 * BN)},
                          "2025": {"profit": str(6 * BN), "total_assets": str(100 * BN), "cfo": str(7 * BN)}}}
    f = report_quality(partial, "Công nghệ Thông tin")["f_score"]
    assert f["evaluated"] < 7 and f["level"] is None
    assert any(c["passed"] is None and c["detail"].startswith("Thiếu") for c in f["criteria"])
    assert next(c for c in f["criteria"] if c["id"] == "no_issue")["detail"] == "Chưa có số liệu phát hành cổ phiếu (chờ lần cập nhật báo cáo sau)"


def test_financial_sectors_and_tickers_without_annual_lines_are_not_scored():
    q = report_quality(STRONG, "Ngân hàng")  # financial sectors are scored from sector ratios instead (below)
    assert q["applicable"] is True and q["f_score"] is None and q["reason"] == "Chưa có chỉ số ngành từ VNDirect (chờ lần cập nhật sau)"
    q = report_quality({"years": {}}, "Công nghệ Thông tin")
    assert q["applicable"] is True and q["f_score"] is None and q["reason"] == "Chưa có số liệu báo cáo chi tiết (chờ lần cập nhật sau)"


def test_equal_looking_values_get_one_more_decimal_and_real_estate_gets_a_note():
    tie = {"annual": {"2023": year(80, 16, 4, 100, 50, 40, 30, 10, 5), "2024": year(90, 19, 15.61, 100, 55, 40, 28, 11, 8),
                      "2025": year(110, 25, 15.63, 100.04, 60, 38, 25, 12, 12)}, "share_issues": []}
    q = report_quality(tie, "Bất động sản")
    roa_up = next(c for c in q["f_score"]["criteria"] if c["id"] == "roa_up")
    assert roa_up["detail"] == "ROA 15,63% so với 15,61% năm 2024"
    assert next(c for c in q["f_score"]["criteria"] if c["id"] == "roa")["detail"] == "ROA 15,6% (lợi nhuận 15,6 tỷ / tài sản đầu kỳ 100 tỷ)"
    assert q["note"] == "Bất động sản: chủ đầu tư thường lãi nhưng dòng tiền kinh doanh âm khi đang đổ tiền vào quỹ đất, dự án (hàng tồn kho); đọc dấu hiệu cùng tiến độ bàn giao."
    assert report_quality(STRONG, "Công nghệ Thông tin")["note"] is None


def _quarters(now: dict, before: dict) -> dict:
    return {"2025-09-30": {k: str(v) for k, v in before.items()}, "2026-09-30": {k: str(v) for k, v in now.items()}}


def test_banks_get_a_health_score_from_sector_ratios_without_a_level():
    ratios = {"kind": "bank", "quarters": _quarters(
        {"ROAA_TR_AVG4Q": 0.0166, "BAD_LOANS_RATIO_AQ": 0.0071, "OVERDUE_LOANS_RATIO_AQ": 0.0086, "PROVISION_BAD_LOANS_AQ": 2.79,
         "NET_INTEREST_MARGIN_TR_AVG5Q": 0.0239, "EQUITY_TO_ASSET_AQ": 0.0935},
        {"ROAA_TR_AVG4Q": 0.0154, "BAD_LOANS_RATIO_AQ": 0.0103, "OVERDUE_LOANS_RATIO_AQ": 0.0120, "PROVISION_BAD_LOANS_AQ": 2.10,
         "NET_INTEREST_MARGIN_TR_AVG5Q": 0.0223, "EQUITY_TO_ASSET_AQ": 0.0950})}
    q = report_quality({"years": {}}, "Ngân hàng", ratios=ratios)
    f = q["f_score"]
    assert q["applicable"] is True and f["kind"] == "health" and f["title"] == "Điểm sức khỏe ngân hàng"
    assert f["year"] == "Q3/2026 so với Q3/2025" and f["score"] == 6 and f["evaluated"] == 7 and f["level"] == "strong"  # one miss of 7
    npl = next(c for c in f["criteria"] if c["id"] == "npl_down")
    assert npl["passed"] is True and npl["detail"] == "Nợ xấu 0,71% so với 1,03% cùng kỳ"
    assert next(c for c in f["criteria"] if c["id"] == "equity_up")["passed"] is False
    assert q["signs"] == []


def test_brokers_and_insurers_use_their_own_criteria_and_a_missing_ratio_set_says_so():
    ratios = {"kind": "insurance", "quarters": _quarters({"ROAA_TR_AVG4Q": 0.0112, "COMBINED_RATIO_TR": 1.22, "NET_MARGIN_TR": 0.083,
                                                           "EQUITY_TO_ASSET_AQ": 0.0847},
                                                          {"ROAA_TR_AVG4Q": 0.0100, "COMBINED_RATIO_TR": 1.25, "NET_MARGIN_TR": 0.070,
                                                           "EQUITY_TO_ASSET_AQ": 0.0900})}
    f = report_quality({"share_issues": []}, "Bảo hiểm", ratios=ratios)["f_score"]
    assert f["title"] == "Điểm sức khỏe bảo hiểm" and f["score"] == 5 and f["evaluated"] == 6
    assert next(c for c in f["criteria"] if c["id"] == "combined_down")["detail"] == "Tỷ lệ kết hợp 122,0% so với 125,0% cùng kỳ"
    q = report_quality({"years": {}}, "Dịch vụ tài chính", ratios=None)
    assert q["applicable"] is True and q["f_score"] is None and q["reason"] == "Chưa có chỉ số ngành từ VNDirect (chờ lần cập nhật sau)"


def test_a_partly_published_latest_quarter_falls_back_to_the_latest_complete_one():
    full = {"ROAA_TR_AVG4Q": 0.019, "BAD_LOANS_RATIO_AQ": 0.012, "OVERDUE_LOANS_RATIO_AQ": 0.02, "PROVISION_BAD_LOANS_AQ": 1.0,
            "NET_INTEREST_MARGIN_TR_AVG5Q": 0.037, "EQUITY_TO_ASSET_AQ": 0.09}
    ratios = {"kind": "bank", "quarters": {"2025-06-30": {k: str(v) for k, v in full.items()}, "2026-06-30": {k: str(v) for k, v in full.items()},
                                           "2026-09-30": {"ROAA_TR_AVG4Q": "0.0192", "NET_INTEREST_MARGIN_TR_AVG5Q": "0.0372"}}}
    f = report_quality({}, "Ngân hàng", ratios=ratios)["f_score"]
    assert f["year"] == "Q2/2026 so với Q2/2025" and f["evaluated"] == 7


def test_health_levels_scale_piotroski_cut_offs_to_the_number_of_criteria():
    from investment_agent.valuation.quality import _level
    assert [_level(s, 7, 7) for s in (7, 6, 5, 2, 1, 0)] == ["strong", "strong", "medium", "medium", "weak", "weak"]
    assert [_level(s, 6, 6) for s in (6, 5, 4, 2, 1)] == ["strong", "strong", "medium", "medium", "weak"]
    assert _level(5, 5, 7) is None and _level(5, 5, 6) == "strong"  # 7 criteria need 6 evaluated, 6 need 5
    assert [_level(s, 9, 9) for s in (9, 8, 7, 3, 2)] == ["strong", "strong", "medium", "medium", "weak"]  # F-Score unchanged
    assert _level(6, 6, 9) is None



def test_owner_entered_bank_figures_add_casa_and_group_two_criteria_only_when_present():
    full = {"ROAA_TR_AVG4Q": 0.019, "BAD_LOANS_RATIO_AQ": 0.012, "OVERDUE_LOANS_RATIO_AQ": 0.02, "PROVISION_BAD_LOANS_AQ": 1.0,
            "NET_INTEREST_MARGIN_TR_AVG5Q": 0.037, "EQUITY_TO_ASSET_AQ": 0.09}
    better = {**full, "ROAA_TR_AVG4Q": 0.02, "BAD_LOANS_RATIO_AQ": 0.011, "OVERDUE_LOANS_RATIO_AQ": 0.019, "PROVISION_BAD_LOANS_AQ": 1.1,
              "NET_INTEREST_MARGIN_TR_AVG5Q": 0.038, "EQUITY_TO_ASSET_AQ": 0.095}
    ratios = {"kind": "bank", "quarters": {"2025-09-30": {k: str(v) for k, v in full.items()}, "2026-09-30": {k: str(v) for k, v in better.items()}}}
    assert report_quality({}, "Ngân hàng", ratios=ratios)["f_score"]["evaluated"] == 7  # nothing entered: seven criteria as before
    groups = {"group1": "450", "group3": "2", "group4": "1", "group5": "2"}
    bank = {"2025-Q3": {**groups, "group2": "8", "demand_deposits": "160", "margin_deposits": "10", "customer_deposits": "500"},
            "2026-Q3": {**groups, "group2": "5", "demand_deposits": "150", "margin_deposits": "10", "customer_deposits": "500"}}
    f = report_quality({}, "Ngân hàng", ratios=ratios, bank=bank_ratio_rows(bank, {}))["f_score"]
    by_id = {c["id"]: c for c in f["criteria"]}
    assert by_id["casa_up"]["passed"] is False and by_id["casa_up"]["detail"] == "CASA 32,0% so với 34,0% Q3/2025 (số nhập tay)"
    assert by_id["group2_down"]["passed"] is True and f["evaluated"] == 9 and f["score"] == 8 and f["level"] == "strong"
    only_now = {"2026-Q3": bank["2026-Q3"]}
    f = report_quality({}, "Ngân hàng", ratios=ratios, bank=bank_ratio_rows(only_now, {}))["f_score"]
    assert {c["id"]: c for c in f["criteria"]}["casa_up"]["detail"] == "Cần số của cùng quý năm trước (Q3/2025): Vietcap chưa có, chưa nhập tay"


def _notes(group2: str, demand: str) -> dict:
    """One quarter of Vietcap's notes in đồng, adding up: loans 1.000, deposits 1.000 (group 2 and demand vary, term takes the rest)."""
    return {"loans": "1000", "group1": str(1000 - 5 - int(group2)), "group2": group2, "group3": "2", "group4": "1", "group5": "2",
            "deposits": "1000", "demand": demand, "term": str(1000 - int(demand) - 20), "savings": "0", "margin": "20", "special": "0"}


def test_vietcaps_notes_score_casa_and_group_two_for_every_bank_with_entered_quarters_first():
    ratios = {"kind": "bank", "quarters": {"2025-09-30": {"ROAA_TR_AVG4Q": "0.019"}, "2026-09-30": {"ROAA_TR_AVG4Q": "0.02"}}}
    notes = {"2025-09-30": _notes("15", "300"), "2026-09-30": _notes("12", "330")}
    by_id = {c["id"]: c for c in report_quality({}, "Ngân hàng", ratios=ratios, bank=bank_ratio_rows({}, notes))["f_score"]["criteria"]}
    assert by_id["casa_up"]["passed"] is True and by_id["casa_up"]["detail"] == "CASA 35,0% so với 32,0% Q3/2025 (Vietcap)"
    assert by_id["group2_down"]["passed"] is True and by_id["group2_down"]["detail"] == "Nợ nhóm 2 1,2% so với 1,5% Q3/2025 (Vietcap)"
    # The owner's entered quarter wins over Vietcap's for that quarter, and each side names its source.
    entered = {"2026-Q3": {"group1": "450", "group2": "5", "group3": "2", "group4": "1", "group5": "2",
                           "demand_deposits": "170", "margin_deposits": "10", "customer_deposits": "500"}}
    by_id = {c["id"]: c for c in report_quality({}, "Ngân hàng", ratios=ratios, bank=bank_ratio_rows(entered, notes))["f_score"]["criteria"]}
    assert by_id["casa_up"]["passed"] is True and by_id["casa_up"]["detail"] == "CASA 36,0% (số nhập tay) so với 32,0% Q3/2025 (Vietcap)"
    # A Vietcap quarter whose parts miss the total is not scored from.
    notes["2025-09-30"] = {**_notes("15", "300"), "group4": "9"}
    by_id = {c["id"]: c for c in report_quality({}, "Ngân hàng", ratios=ratios, bank=bank_ratio_rows({}, notes))["f_score"]["criteria"]}
    assert by_id["group2_down"]["passed"] is None and by_id["casa_up"]["passed"] is True


def with_finance(income, expense, pbt, y="2025"):
    rec = {"annual": {k: dict(v) for k, v in STRONG["annual"].items()}, "share_issues": STRONG["share_issues"]}
    rec["annual"][y].update(fin_income=str(income * BN), fin_expense=str(expense * BN), pbt=str(pbt * BN))
    return rec


def finance_sign(rec):
    return next(s for s in report_quality(rec, "Công nghệ Thông tin")["signs"] if s["id"] == "financial_profit")


def test_profit_resting_on_financial_income_is_a_sign_from_thirty_percent():
    s = finance_sign(with_finance(40, 10, 100))  # 30 of 100 before tax
    assert (s["flag"], s["label"]) == (True, "Lợi nhuận phụ thuộc thu nhập tài chính")
    assert s["detail"] == "Năm 2025: lãi tài chính ròng 30 tỷ (doanh thu tài chính 40 tỷ − chi phí tài chính 10 tỷ), bằng 30,0% lợi nhuận trước thuế 100 tỷ"
    assert s["rule"] == "lãi tài chính ròng từ 30% lợi nhuận trước thuế (doanh thu tài chính gồm lãi tiền gửi, lãi tỷ giá, cổ tức)"
    assert finance_sign(with_finance(39, 10, 100))["flag"] is False
    assert finance_sign(with_finance(5, 20, 100))["flag"] is False  # a net financial cost depends on nothing


def test_a_loss_before_tax_or_missing_lines_leave_the_sign_unread():
    loss = finance_sign(with_finance(40, 10, -5))
    assert loss["flag"] is None and "lỗ trước thuế" in loss["detail"]
    assert finance_sign(STRONG)["flag"] is None


def with_other(now_st, now_lt, before_st=None, before_lt=None):
    rec = {"annual": {k: dict(v) for k, v in STRONG["annual"].items()}, "share_issues": STRONG["share_issues"]}  # total assets 105 tỷ in 2025
    rec["annual"]["2025"].update(other_receivables=str(now_st * BN), other_receivables_lt=str(now_lt * BN))
    if before_st is not None:
        rec["annual"]["2024"].update(other_receivables=str(before_st * BN), other_receivables_lt=str(before_lt * BN))  # 100 tỷ in 2024
    return next(s for s in report_quality(rec, "Công nghệ Thông tin")["signs"] if s["id"] == "other_receivables")


def test_large_other_receivables_are_a_sign_from_a_tenth_of_total_assets_or_doubling():
    big = with_other(8, 3)  # 11 of 105
    assert (big["flag"], big["label"]) == (True, "Phải thu khác lớn")
    assert big["detail"] == "Năm 2025: phải thu khác 11 tỷ (ngắn hạn 8 tỷ, dài hạn 3 tỷ), bằng 10,5% tổng tài sản 105 tỷ"
    assert big["rule"] == ("phải thu khác và phải thu về cho vay (ngắn và dài hạn; từ 2026 Thông tư 99 gộp cho vay vào phải thu khác) từ 10% tổng tài sản, "
                           "hoặc gấp đôi năm trước khi năm trước đã từ 1% tổng tài sản")
    assert with_other(6, 2, 2, 1)["flag"] is True   # 8 against 3 a year before (3% of 100): more than doubled
    assert with_other(1, 0, 0.3, 0.1)["flag"] is False  # doubled, but from 0,4% of total assets: not material
    small = with_other(4, 1, 3, 1)
    assert small["flag"] is False and "so với 4 tỷ năm 2024" in small["detail"]


def test_other_receivables_missing_leave_the_sign_unread():
    s = next(s for s in report_quality(STRONG, "Công nghệ Thông tin")["signs"] if s["id"] == "other_receivables")
    assert s["flag"] is None and "Thiếu phải thu khác" in s["detail"]


def with_prepay(now, before=None):
    rec = {"annual": {k: dict(v) for k, v in STRONG["annual"].items()}, "share_issues": STRONG["share_issues"]}  # total assets 105 / 100 tỷ
    rec["annual"]["2025"]["prepay_suppliers"] = str(now * BN)
    if before is not None:
        rec["annual"]["2024"]["prepay_suppliers"] = str(before * BN)
    return next(s for s in report_quality(rec, "Công nghệ Thông tin")["signs"] if s["id"] == "prepay_suppliers")


def test_large_prepayments_to_suppliers_are_a_sign_from_a_tenth_of_total_assets_or_doubling():
    big = with_prepay(11)
    assert (big["flag"], big["label"]) == (True, "Trả trước người bán lớn")
    assert big["detail"] == "Năm 2025: trả trước cho người bán 11 tỷ, bằng 10,5% tổng tài sản 105 tỷ"
    assert big["rule"] == ("trả trước cho người bán (ngắn hạn) từ 10% tổng tài sản, hoặc gấp đôi năm trước khi năm trước đã từ 1% tổng tài sản; "
                           "khoản này thu hồi bằng hàng hóa, dịch vụ chứ không bằng tiền")
    assert with_prepay(7, 3)["flag"] is True and with_prepay(1, 0.4)["flag"] is False
    calm = with_prepay(4, 3)
    assert calm["flag"] is False and calm["detail"].endswith("; so với 3 tỷ năm 2024")
    none = next(s for s in report_quality(STRONG, "Công nghệ Thông tin")["signs"] if s["id"] == "prepay_suppliers")
    assert none["flag"] is None and "Thiếu trả trước cho người bán" in none["detail"]


def test_loans_merged_into_other_receivables_from_2026_do_not_read_as_doubling():
    # Thông tư 99 (from 2026) drops "phải thu về cho vay": loans move into other receivables. Both years count them, so the move alone
    # is no jump: 2024 other 3 + loans 5 against 2025 other 8 + loans 0.
    rec = {"annual": {k: dict(v) for k, v in STRONG["annual"].items()}, "share_issues": STRONG["share_issues"]}
    rec["annual"]["2024"].update(other_receivables=str(2 * BN), other_receivables_lt=str(1 * BN), st_loans_receivable=str(4 * BN), lt_loans_receivable=str(1 * BN))
    rec["annual"]["2025"].update(other_receivables=str(7 * BN), other_receivables_lt=str(1 * BN), st_loans_receivable="0", lt_loans_receivable="0")
    s = next(x for x in report_quality(rec, "Công nghệ Thông tin")["signs"] if x["id"] == "other_receivables")
    assert s["flag"] is False
    assert s["detail"] == ("Năm 2025: phải thu khác và cho vay 8 tỷ (phải thu khác ngắn hạn 7 tỷ, dài hạn 1 tỷ), bằng 7,6% tổng tài sản 105 tỷ; "
                           "so với 8 tỷ năm 2024 (gồm 5 tỷ cho vay)")


def paper(income, received, pbt, before=None):
    rec = {"annual": {k: dict(v) for k, v in STRONG["annual"].items()}, "share_issues": STRONG["share_issues"]}
    rec["annual"]["2025"].update(fin_income=str(income * BN), interest_received=str(received * BN), pbt=str(pbt * BN))
    if before:
        rec["annual"]["2024"].update(fin_income=str(before[0] * BN), interest_received=str(before[1] * BN))
    return next(s for s in report_quality(rec, "Công nghệ Thông tin")["signs"] if s["id"] == "paper_income")


def test_financial_income_mostly_not_received_in_cash_is_a_sign():
    s = paper(37.66, 3.47, 48.76, before=(3.33, 3.84))  # VCG-like: 9% of the income came in as cash
    assert (s["flag"], s["label"]) == (True, "Thu nhập tài chính chưa thu được tiền")
    assert s["detail"] == ("Năm 2025: doanh thu tài chính 37,7 tỷ, tiền thu lãi, cổ tức và lợi nhuận được chia 3,5 tỷ (9,2%); lợi nhuận trước thuế 48,8 tỷ; "
                           "năm 2024: 3,3 tỷ và 3,8 tỷ (115,3%)")
    assert s["rule"] == ("tiền thu lãi cho vay, cổ tức và lợi nhuận được chia dưới 50% doanh thu tài chính, khi doanh thu tài chính từ 10% lợi nhuận "
                         "trước thuế (hoặc doanh nghiệp lỗ); doanh thu tài chính còn gồm lãi tỷ giá và lãi bán khoản đầu tư, thu tiền ở dòng khác: "
                         "đọc thuyết minh")
    assert paper(29.77, 20.01, 130.44)["flag"] is False      # FPT-like: two thirds received
    assert paper(5, 1, 100)["flag"] is False                 # 5% of profit before tax: not material
    assert paper(5, 1, -20)["flag"] is True                  # a loss-making company booking interest it does not collect


def test_without_the_cash_line_or_financial_income_the_sign_is_not_read():
    assert next(s for s in report_quality(STRONG, "Công nghệ Thông tin")["signs"] if s["id"] == "paper_income")["flag"] is None
    none = paper(0, 0, 50)
    assert none["flag"] is None and "không có doanh thu tài chính" in none["detail"]
