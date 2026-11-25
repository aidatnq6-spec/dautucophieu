from investment_agent.market.statements import LINES, LINES_VERSION


def test_receivable_lines_are_kept_and_records_before_them_are_fetched_again():
    names = {(m, c): n for (m, c), n in LINES.items()}
    assert names[(1, 11310)] == "ar_customers" and names[(1, 11320)] == "prepay_suppliers" and names[(1, 11345)] == "st_loans_receivable"
    assert names[(1, 11350)] == "other_receivables" and names[(1, 11390)] == "bad_debt_st" and names[(1, 12100)] == "receivables_lt"
    assert names[(1, 12110)] == "ar_customers_lt" and names[(1, 12140)] == "lt_loans_receivable" and names[(1, 12180)] == "other_receivables_lt"
    assert names[(1, 12190)] == "bad_debt_lt"
    assert names[(3, 32700)] == "interest_received"  # tiền thu lãi cho vay, cổ tức và lợi nhuận được chia, for Lợi nhuận giấy
    assert LINES_VERSION >= 5


def test_inventory_at_cost_and_its_provision_are_kept_owner_22_11_2026():
    """Khối Tồn kho: 11410 at cost and 11490 the provision for a fall in value (MWG 2021: 29.850,1 and −682,8 tỷ); a new layout version
    makes each ticker fetch its whole history once."""
    names = {(m, c): n for (m, c), n in LINES.items()}
    assert names[(1, 11410)] == "inventory_gross" and names[(1, 11490)] == "inventory_provision" and names[(1, 11400)] == "inventory"
    assert LINES_VERSION >= 6  # 7 (review 23/11/2026) reads the history again for the update days


def test_fixed_asset_investment_property_and_construction_lines_are_kept_owner_25_11_2026():
    """Tài sản cố định (spec 25/11/2026): names from v4/financial_models; HPG 2021: 12210 68.744,1, 12460 8.289,3, 12270 536,7 tỷ."""
    names = {(m, c): n for (m, c), n in LINES.items()}
    assert names[(1, 12210)] == "ppe_net" and names[(1, 12220)] == "ppe_gross" and names[(1, 12230)] == "ppe_depreciation"
    assert names[(1, 12240)] == "ppe_lease_net"
    assert names[(1, 12270)] == "intangible_net" and names[(1, 12280)] == "intangible_gross" and names[(1, 12290)] == "intangible_amortisation"
    assert names[(1, 12400)] == "property_net" and names[(1, 12410)] == "property_gross" and names[(1, 12420)] == "property_depreciation"
    assert names[(1, 12460)] == "cip" and names[(1, 12300)] == "cip_old"
    assert LINES_VERSION >= 8


def test_prepaid_expense_lines_are_kept_owner_25_11_2026():
    """Chi phí trả trước (spec 25/11/2026): HPG 2021 11510 296,7 and 12610 3.171,4 tỷ; 31160 the cash flow change."""
    names = {(m, c): n for (m, c), n in LINES.items()}
    assert names[(1, 11510)] == "prepaid_st" and names[(1, 12610)] == "prepaid_lt" and names[(3, 31160)] == "prepaid_change"
    assert LINES_VERSION >= 9


def test_goodwill_and_its_amortisation_are_kept_owner_25_11_2026():
    """Lợi thế thương mại (spec 25/11/2026): NVL 2021 12690 5.104,0 tỷ; 31111 the amortisation added back in operating cash flow."""
    names = {(m, c): n for (m, c), n in LINES.items()}
    assert names[(1, 12690)] == "goodwill" and names[(3, 31111)] == "goodwill_amort"
    assert LINES_VERSION >= 10


def test_borrowing_cash_flows_and_unrealised_exchange_differences_are_kept_owner_25_11_2026():
    """Nợ vay (spec 25/11/2026): 33300 borrowings received, 33400 principal repaid, 31100 unrealised exchange gains and losses."""
    names = {(m, c): n for (m, c), n in LINES.items()}
    assert names[(3, 33300)] == "borrow_in" and names[(3, 33400)] == "borrow_out" and names[(3, 31100)] == "fx_unrealised"
    assert LINES_VERSION >= 11


def test_equity_parts_and_share_cash_flows_are_kept_owner_25_11_2026():
    """Vốn chủ sở hữu (spec 25/11/2026): HAG 2021 14120 0 (2020: 3.263,9), 14200 −4.467,1; 33100 shares issued, 33200 bought back."""
    names = {(m, c): n for (m, c), n in LINES.items()}
    assert names[(1, 14120)] == "share_premium" and names[(1, 14140)] == "treasury_shares" and names[(1, 14160)] == "equity_fx"
    assert names[(1, 14170)] == "dev_fund" and names[(1, 14200)] == "retained" and names[(3, 33100)] == "issue_cash" and names[(3, 33200)] == "buyback_cash"
    assert LINES_VERSION >= 12
