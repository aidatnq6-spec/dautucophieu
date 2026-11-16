from investment_agent.market.statements import LINES, LINES_VERSION


def test_receivable_lines_are_kept_and_records_before_them_are_fetched_again():
    names = {(m, c): n for (m, c), n in LINES.items()}
    assert names[(1, 11310)] == "ar_customers" and names[(1, 11320)] == "prepay_suppliers" and names[(1, 11345)] == "st_loans_receivable"
    assert names[(1, 11350)] == "other_receivables" and names[(1, 11390)] == "bad_debt_st" and names[(1, 12100)] == "receivables_lt"
    assert names[(1, 12110)] == "ar_customers_lt" and names[(1, 12140)] == "lt_loans_receivable" and names[(1, 12180)] == "other_receivables_lt"
    assert names[(1, 12190)] == "bad_debt_lt"
    assert names[(3, 32700)] == "interest_received"  # tiền thu lãi cho vay, cổ tức và lợi nhuận được chia, for Lợi nhuận giấy
    assert LINES_VERSION == 5
