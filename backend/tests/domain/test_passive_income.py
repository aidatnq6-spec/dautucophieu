from datetime import date
from decimal import Decimal

from investment_agent.domain.passive_income import passive_income

TODAY = date(2026, 10, 27)


def test_capital_needed_income_now_and_time_to_reach_it_with_monthly_contributions():
    p = passive_income(target=Decimal(10_000_000), rate=Decimal("5.63"), capital=Decimal(1_880_000_000), contribution=Decimal(8_000_000), today=TODAY)
    assert p["required"] == "2131438721"          # 120 tr a year at 5,63%
    assert p["income_now"] == "8820333" and p["progress"] == "0.8820"
    assert p["months"] == 15 and p["reached_on"] == "2028-01"   # compounding monthly at 5,63%/12, adding 8 tr each month


def test_already_there():
    p = passive_income(target=Decimal(5_000_000), rate=Decimal("6"), capital=Decimal(1_200_000_000), contribution=Decimal(0), today=TODAY)
    assert p["months"] == 0 and p["reached_on"] == "2026-10" and p["progress"] == "1.0000"


def test_without_contributions_growth_alone_counts_and_very_long_horizons_say_so():
    p = passive_income(target=Decimal(10_000_000), rate=Decimal("6"), capital=Decimal(1_000_000_000), contribution=Decimal(0), today=TODAY)
    assert p["months"] == 139  # 1 tỷ → 2 tỷ at 6%/12 a month
    far = passive_income(target=Decimal(100_000_000), rate=Decimal("1"), capital=Decimal(1_000_000), contribution=Decimal(0), today=TODAY)
    assert far["months"] is None and far["reached_on"] is None


def test_no_capital_yet_still_gives_the_requirement():
    p = passive_income(target=Decimal(10_000_000), rate=Decimal("6"), capital=None, contribution=Decimal(8_000_000), today=TODAY)
    assert p["required"] == "2000000000" and p["income_now"] is None and p["months"] is not None


def test_income_now_is_counted_layer_by_layer():
    from investment_agent.domain.passive_income import income_by_layer
    lines = income_by_layer(deposit=Decimal(843_522_000), deposit_rate=Decimal("5.63"), bond=Decimal(150_200_000), bond_rate=Decimal("7"),
                            dividends_12m=Decimal(12_000_000))
    assert lines == {"deposit": "3957524", "bond": "876167", "dividends": "1000000", "total": "5833691"}  # per month; gold, cash, crypto pay nothing


def test_a_given_income_now_replaces_capital_times_rate():
    p = passive_income(target=Decimal(10_000_000), rate=Decimal("6"), capital=Decimal(1_000_000_000), contribution=Decimal(0), today=TODAY,
                       income_now=Decimal(4_000_000))
    assert p["income_now"] == "4000000" and p["progress"] == "0.4000"


def test_a_stock_rate_entered_by_hand_replaces_the_dividends():
    from investment_agent.domain.passive_income import income_by_layer
    lines = income_by_layer(deposit=Decimal(0), deposit_rate=Decimal("5.63"), bond=Decimal(0), bond_rate=Decimal("7"), dividends_12m=Decimal(12_000_000),
                            stocks=Decimal(802_743_828), stock_rate=Decimal("12"))
    assert lines["stocks"] == "8027438" and lines["dividends"] == "0" and lines["total"] == "8027438"  # 802,7 tr × 12% / 12
