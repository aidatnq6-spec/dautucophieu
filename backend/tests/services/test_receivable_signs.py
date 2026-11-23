import json

from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.statements import StatementStore
from investment_agent.services.receivable_signs import SIGNS, receivable_signs

BN = 10**9


def year(**v):
    return {k: str(x * BN) for k, x in v.items()}


def data(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("AAA\nBBB\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-11-11", "source": "t", "level": 2, "sectors": {
        "AAA": "Xây dựng và Vật liệu", "BBB": "Xây dựng và Vật liệu", "VCB": "Ngân hàng"}}), encoding="utf-8")
    base = dict(revenue=100, gross_profit=20, profit=10, total_assets=100, current_assets=50, current_liabilities=40, long_liabilities=10,
                receivables=10, cfo=12)
    fs = FundamentalsStore(tmp_path / "fundamentals")
    fs.save({"symbol": "AAA", "annual": {"2024": year(**base), "2025": year(**{**base, "fin_income": 40, "fin_expense": 2, "pbt": 50,
                                                                              "interest_received": 3, "other_receivables": 20, "other_receivables_lt": 0,
                                                                              "prepay_suppliers": 1})}, "share_issues": []})
    fs.save({"symbol": "BBB", "annual": {"2024": year(**base), "2025": year(**{**base, "fin_income": 1, "fin_expense": 1, "pbt": 50,
                                                                              "interest_received": 1, "other_receivables": 1, "other_receivables_lt": 0,
                                                                              "prepay_suppliers": 1})}, "share_issues": []})
    StatementStore(tmp_path / "statements").save({"symbol": "AAA", "quarters": {}, "years": {}})
    return tmp_path


def test_each_watched_non_financial_ticker_gets_its_receivable_signs_most_first(tmp_path):
    rows = receivable_signs(data(tmp_path))
    assert [r["symbol"] for r in rows] == ["AAA", "BBB", "VCB"]
    aaa, bbb, vcb = rows
    assert vcb["signs"] == {"provision_cut": None, "accrued_outpace": None}  # a bank has only the bank signs (Chất lượng tài sản ngân hàng, owner 23/11/2026)
    assert aaa["signs"]["other_receivables"] is True and aaa["signs"]["paper_income"] is True and aaa["signs"]["financial_profit"] is True
    assert aaa["count"] == 3 and bbb["count"] == 0
    assert aaa["signs"]["other_high"] is None  # no quarters stored: not read
    assert [k for k, _ in SIGNS][:3] == ["other_receivables", "other_high", "prepay_suppliers"]


def test_a_bank_whose_provisions_were_cut_while_bad_debt_grew_has_the_sign_with_its_figures(tmp_path):
    """Dự phòng đi vào lợi nhuận (owner, 23/11/2026): VNDirect's lines and Vietcap's groups only, as all of this board is public figures."""
    from investment_agent.market.bank_notes import BankNoteStore
    d = data(tmp_path)
    StatementStore(d / "statements-financial").save({"symbol": "VCB", "kind": "bank", "years": {}, "quarters": {
        "2025-Q3": {"provision_expense": str(1000 * BN), "ppop": str(4000 * BN)}, "2026-Q3": {"provision_expense": str(600 * BN), "ppop": str(4500 * BN)}}})
    groups = lambda g3: {"group1": str(1000 * BN), "group2": str(10 * BN), "group3": str(g3 * BN), "group4": str(5 * BN), "group5": str(5 * BN),  # noqa: E731
                         "loans": str((1020 + g3) * BN)}
    BankNoteStore(d / "bank-notes").save({"symbol": "VCB", "fetched_at": "2026-11-20T00:00:00+00:00", "source": "vietcap:iq",
                                          "quarters": {"2026-06-30": groups(10), "2026-09-30": groups(15)}})
    vcb = next(r for r in receivable_signs(d) if r["symbol"] == "VCB")
    assert ("provision_cut", "Lợi nhuận đỡ bởi giảm trích lập") in SIGNS and vcb["signs"]["provision_cut"] is True and vcb["count"] == 1
    assert vcb["details"]["provision_cut"] == ("Chi phí dự phòng quý 3/2026 giảm 40% so cùng kỳ trong khi nợ nhóm 3–5 tăng 25% so quý trước; "
                                               "chi phí dự phòng bằng 13% lợi nhuận trước dự phòng.")


def test_a_bank_whose_accrued_interest_outpaced_its_interest_income_has_the_sign_with_its_figures(tmp_path):
    d = data(tmp_path)
    StatementStore(d / "statements-financial").save({"symbol": "VCB", "kind": "bank", "years": {}, "quarters": {
        "2025-Q3": {"interest_income": str(1000 * BN), "accrued_interest": str(500 * BN)},
        "2026-Q3": {"interest_income": str(1100 * BN), "accrued_interest": str(700 * BN)}}})
    vcb = next(r for r in receivable_signs(d) if r["symbol"] == "VCB")
    assert ("accrued_outpace", "Lãi dự thu tăng nhanh hơn thu nhập lãi") in SIGNS and vcb["signs"]["accrued_outpace"] is True
    assert vcb["details"]["accrued_outpace"] == ("Lãi, phí phải thu quý 3/2026 tăng 40% so cùng kỳ, thu nhập lãi tăng 10%; lãi dự thu bằng 64% thu nhập lãi "
                                                 "của quý (cùng kỳ 50%).")


def test_a_fall_is_written_as_a_fall_not_as_a_rise(tmp_path):
    """Review 23/11/2026: the sign fires when interest income falls too; the words follow each figure's sign."""
    d = data(tmp_path)
    StatementStore(d / "statements-financial").save({"symbol": "VCB", "kind": "bank", "years": {}, "quarters": {
        "2025-Q3": {"interest_income": str(1000 * BN), "accrued_interest": str(500 * BN)},
        "2026-Q3": {"interest_income": str(800 * BN), "accrued_interest": str(525 * BN)}}})
    vcb = next(r for r in receivable_signs(d) if r["symbol"] == "VCB")
    assert vcb["signs"]["accrued_outpace"] is True
    assert vcb["details"]["accrued_outpace"].startswith("Lãi, phí phải thu quý 3/2026 tăng 5% so cùng kỳ, thu nhập lãi giảm 20%;")


def test_no_bad_debt_the_quarter_before_gives_no_growth_to_state_and_does_not_break_the_board(tmp_path):
    from investment_agent.market.bank_notes import BankNoteStore
    d = data(tmp_path)
    StatementStore(d / "statements-financial").save({"symbol": "VCB", "kind": "bank", "years": {}, "quarters": {
        "2025-Q3": {"provision_expense": str(1000 * BN), "ppop": str(4000 * BN)}, "2026-Q3": {"provision_expense": str(600 * BN), "ppop": str(4500 * BN)}}})
    groups = lambda g3: {"group1": str(1000 * BN), "group2": "0", "group3": str(g3), "group4": "0", "group5": "0", "loans": str(1000 * BN + g3)}  # noqa: E731
    BankNoteStore(d / "bank-notes").save({"symbol": "VCB", "fetched_at": "2026-11-20T00:00:00+00:00", "source": "vietcap:iq",
                                          "quarters": {"2026-06-30": groups(0), "2026-09-30": groups(450_000_000)}})  # đồng
    vcb = next(r for r in receivable_signs(d) if r["symbol"] == "VCB")
    assert vcb["signs"]["provision_cut"] is True
    # 450 million đồng is not "0 tỷ" (review 23/11/2026 (2)): one decimal, half up
    assert vcb["details"]["provision_cut"].startswith("Chi phí dự phòng quý 3/2026 giảm 40% so cùng kỳ trong khi nợ nhóm 3–5 tăng từ 0,0 lên 0,5 tỷ")


def test_one_unreadable_bank_file_leaves_that_bank_unread_and_the_board_standing(tmp_path):
    d = data(tmp_path)
    (d / "bank-notes").mkdir()
    (d / "bank-notes" / "VCB.json").write_text('{"symbol": "VCB", "quart', encoding="utf-8")  # cut short by a power loss
    rows = receivable_signs(d)
    assert [r["symbol"] for r in rows] == ["AAA", "BBB", "VCB"] and rows[2]["signs"] == {"provision_cut": None, "accrued_outpace": None}
    for odd in ('{"symbol": "VCB", "quarters": ["2026-09-30"]}', '{"symbol": "VCB", "quarters": {"bad": {"group1": "1", "group2": "1", '
                '"group3": "1", "group4": "1", "group5": "1"}}}'):  # valid JSON of the wrong shape
        (d / "bank-notes" / "VCB.json").write_text(odd, encoding="utf-8")
        assert receivable_signs(d)[2]["signs"] == {"provision_cut": None, "accrued_outpace": None}


def test_tỷ_amounts_keep_their_sign_and_one_decimal():
    from investment_agent.services.receivable_signs import _ty
    # -0,45 kept its sign only as "-0" before (review 23/11/2026 (3)); a value that rounds to zero shows no sign, as formatDecimal on the web
    assert (_ty("-0.45"), _ty("-1234.56"), _ty("-0.04"), _ty("0.45"), _ty("2.25")) == ("-0,5", "-1.234,6", "0,0", "0,5", "2,3")


def test_a_gross_loss_with_the_provision_flat_is_a_sign_with_its_figures(tmp_path):
    """Bán dưới giá vốn nhưng dự phòng không tăng (owner, 23/11/2026)."""
    d = data(tmp_path)
    q = lambda gp, prov: {"gross_profit": str(gp * BN), "inventory_gross": str(300 * BN), "inventory_provision": str(-prov * BN),  # noqa: E731
                          "inventory": str((300 - prov) * BN), "total_assets": str(1000 * BN)}
    StatementStore(d / "statements").save({"symbol": "AAA", "years": {}, "quarters": {"2026-Q2": q(20, 6), "2026-Q3": q(-5, 6)}})
    aaa = next(r for r in receivable_signs(d) if r["symbol"] == "AAA")
    assert ("gross_loss", "Bán dưới giá vốn, dự phòng không tăng") in SIGNS and aaa["signs"]["gross_loss"] is True
    assert aaa["details"]["gross_loss"] == "Lỗ gộp 5,0 tỷ trong quý 3/2026; tỷ lệ trích lập dự phòng tồn kho 2,0% (quý trước 2,0%)."


def test_days_up_while_the_provision_thins_is_a_sign_with_its_figures(tmp_path):
    """Dự phòng mỏng dần trong khi hàng tồn lâu hơn (owner, 23/11/2026)."""
    d = data(tmp_path)
    qs = {f"{y}-Q{n}": {"cogs": str(100 * BN)} for y in (2024, 2025, 2026) for n in range(1, 5) if f"{y}-Q{n}" <= "2026-Q3"}
    for k, gross, prov in (("2025-Q3", 200, 10), ("2026-Q3", 260, 10)):
        qs[k].update({"inventory_gross": str(gross * BN), "inventory_provision": str(-prov * BN), "inventory": str((gross - prov) * BN),
                      "total_assets": str(1000 * BN), "gross_profit": str(10 * BN)})
    StatementStore(d / "statements").save({"symbol": "AAA", "years": {}, "quarters": qs})
    aaa = next(r for r in receivable_signs(d) if r["symbol"] == "AAA")
    assert ("cover_thinning", "Dự phòng mỏng dần, hàng tồn lâu hơn") in SIGNS and aaa["signs"]["cover_thinning"] is True
    assert aaa["details"]["cover_thinning"] == ("Tồn kho đủ 228 ngày giá vốn (cùng kỳ 173 ngày) trong khi tỷ lệ trích lập dự phòng còn 3,9% "
                                                "(cùng kỳ 5,0%), quý 3/2026.")


def test_a_q4_provision_the_audit_changed_is_a_sign_with_both_balances(tmp_path):
    """Dự phòng chốt khi kiểm toán (owner, 23/11/2026): told once for a held ticker through the signs note."""
    d = data(tmp_path)
    StatementStore(d / "statements").save({"symbol": "AAA", "years": {"2025": {"inventory_provision": str(-682 * BN)}},
                                           "quarters": {"2025-Q4": {"inventory_provision": str(-600 * BN)}},
                                           "years_modified": {"2025": "2026-04-01"}, "quarters_created": {"2025-Q4": "2026-01-30"}})
    aaa = next(r for r in receivable_signs(d) if r["symbol"] == "AAA")
    assert ("audit_gap", "Dự phòng tồn kho quý 4 khác số năm cập nhật sau") in SIGNS and aaa["signs"]["audit_gap"] is True
    # never "đã kiểm toán": the source's year is updated later, and the page says only when (owner, 23/11/2026)
    assert aaa["details"]["audit_gap"] == ("Năm 2025: dự phòng giảm giá tồn kho cuối quý 4 tự lập 600,0 tỷ; số năm VNDirect cập nhật ngày 01/04/2026 "
                                           "là 682,0 tỷ (thêm 82,0 tỷ). Đối chiếu báo cáo năm đã kiểm toán.")
    # a year five times both its Q3 and the next Q2: marked as a possible source error
    StatementStore(d / "statements").save({"symbol": "AAA", "years": {"2025": {"inventory_provision": str(-405 * BN)}},
                                           "quarters": {k: {"inventory_provision": str(-v * BN)} for k, v in
                                                        (("2025-Q3", 34), ("2025-Q4", 35), ("2026-Q1", 35), ("2026-Q2", 34))},
                                           "years_modified": {"2025": "2026-07-31"}, "quarters_created": {"2025-Q4": "2026-01-30"}})
    aaa = next(r for r in receivable_signs(d) if r["symbol"] == "AAA")
    # VCG's 405,8 tỷ was real (a business combination, audited report p.41): a jump is not called an error (owner, 23/11/2026)
    assert aaa["details"]["audit_gap"].endswith("Số năm nhảy vọt so với các quý quanh đó: đối chiếu thuyết minh (có thể do hợp nhất kinh doanh, "
                                                "thoái vốn, hoặc lỗi dữ liệu nguồn).")


def test_an_output_price_down_is_a_sign_only_for_a_ticker_its_value_chain_ties_to_a_goods_price(tmp_path):
    """Giá đầu ra giảm nhưng dự phòng không đổi (owner, 23/11/2026): DCM to urea; AAA (construction) has no such sign at all."""
    d = data(tmp_path)
    (d / "market-symbols.txt").write_text("AAA\nBBB\nVCB\nDCM\n", encoding="utf-8")
    ind = json.loads((d / "industries.json").read_text(encoding="utf-8"))
    ind["sectors"]["DCM"] = "Hóa chất"
    (d / "industries.json").write_text(json.dumps(ind), encoding="utf-8")
    q = lambda gross, prov: {"inventory_gross": str(gross * BN), "inventory_provision": str(-prov * BN), "inventory": str((gross - prov) * BN),  # noqa: E731
                             "total_assets": str(1000 * BN), "gross_profit": str(10 * BN)}
    StatementStore(d / "statements").save({"symbol": "DCM", "years": {}, "quarters": {"2025-Q3": q(200, 10), "2026-Q3": q(260, 10)}})
    (d / "macro").mkdir()
    (d / "macro" / "com_urea.json").write_text(json.dumps({"observations": [{"date": "2025-09-01", "value": "400"},
                                                                            {"date": "2026-09-01", "value": "340"}]}), encoding="utf-8")
    rows = {r["symbol"]: r for r in receivable_signs(d)}
    assert ("price_drop", "Giá bán giảm, dự phòng không tăng") in SIGNS and rows["DCM"]["signs"]["price_drop"] is True
    assert rows["DCM"]["details"]["price_drop"] == ("Giá urê thế giới (Trung Đông, World Bank) cuối quý 3/2026 giảm 15% so cùng kỳ (400 → 340) "
                                                    "trong khi tỷ lệ trích lập dự phòng tồn kho 3,9% (cùng kỳ 5,0%).")
    assert "price_drop" not in rows["AAA"]["signs"]


def test_lending_against_equity_is_a_sign_with_its_figure(tmp_path):
    from investment_agent.market.statements import StatementStore
    d = data(tmp_path)
    B = 10**9
    StatementStore(d / "statements").save({"symbol": "AAA", "years": {}, "quarters": {
        "2025-Q1": {"other_receivables": str(100 * B), "other_receivables_lt": "0", "st_loans_receivable": "0", "lt_loans_receivable": "0", "equity": str(1000 * B)},
        "2026-Q1": {"other_receivables": str(350 * B), "other_receivables_lt": "0", "equity": str(1000 * B)}}})
    aaa = next(r for r in receivable_signs(d) if r["symbol"] == "AAA")
    assert ("lending", "Cho vay lớn so với vốn chủ") in SIGNS and aaa["signs"]["lending"] is True
    assert aaa["details"]["lending"] == "Cho vay và phải thu khác bằng 35% vốn chủ (quý 1/2026); xem Sổ phải thu bên liên quan trên hồ sơ mã."


def test_inventory_growing_faster_than_cost_of_sales_is_a_sign_with_its_figures(tmp_path):
    from investment_agent.market.statements import StatementStore
    d = data(tmp_path)
    B = 10**9
    q = lambda inv, cogs: {"inventory": str(inv * B), "cogs": str(cogs * B), "total_assets": str(1000 * B)}  # noqa: E731
    StatementStore(d / "statements").save({"symbol": "AAA", "years": {}, "quarters": {f"2024-Q{n}": q(200, 100) for n in range(1, 5)}
                                           | {f"2025-Q{n}": q(300, 110) for n in range(1, 5)}})
    aaa = next(r for r in receivable_signs(d) if r["symbol"] == "AAA")
    assert ("inventory_fast", "Tồn kho tăng nhanh hơn giá vốn") in SIGNS and aaa["signs"]["inventory_fast"] is True
    assert aaa["details"]["inventory_fast"] == "Tồn kho tăng 50% so cùng kỳ, giá vốn bốn quý tăng 10%; tồn kho đủ 249 ngày (cùng kỳ 183 ngày)."
