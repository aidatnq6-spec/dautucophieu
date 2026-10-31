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
    assert [s["flag"] for s in q["signs"]] == [False, False, False]


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

