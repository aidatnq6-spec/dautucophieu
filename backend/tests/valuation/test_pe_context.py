from test_statement_table import q

from investment_agent.valuation.statement_table import pe_context


def quarters(before, after):
    """Four quarters of 2024 and four of 2025, each with the given parent profit (tỷ đồng)."""
    return {**{f"2024-Q{k}": q(100, before) for k in range(1, 5)}, **{f"2025-Q{k}": q(100, after) for k in range(1, 5)}}


def test_a_profit_that_halved_says_the_pe_is_high_because_earnings_fell():
    c = pe_context(quarters(50, 25))
    assert (c["quarter"], c["year_ago"], c["change"], c["kind"]) == ("2025-Q4", "2024-Q4", "-0.5000", "earnings_drop")
    assert (c["ttm"], c["ttm_year_ago"]) == ("100000000000", "200000000000")


def test_a_profit_that_jumped_warns_a_low_pe_may_not_last():
    assert pe_context(quarters(50, 100))["kind"] == "earnings_spike"


def test_a_loss_over_four_quarters_says_pe_means_nothing():
    assert pe_context(quarters(50, -10))["kind"] == "loss"


def test_an_ordinary_change_says_nothing():
    c = pe_context(quarters(50, 55))
    assert c["kind"] is None and c["change"] == "0.1000"


def test_without_the_year_before_there_is_nothing_to_compare():
    only_one_year = {f"2025-Q{k}": q(100, 25) for k in range(1, 5)}
    assert pe_context(only_one_year) is None
    assert pe_context({}) is None
