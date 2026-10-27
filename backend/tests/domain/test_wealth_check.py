from datetime import date
from decimal import Decimal

from investment_agent.domain.wealth_check import wealth_check

TODAY = date(2026, 10, 27)


def test_short_of_the_age_rule_says_how_much_more_to_save_each_month():
    c = wealth_check(income=Decimal(25_000_000), expenses=Decimal(17_000_000), birth_year=1989, today=TODAY)
    assert c == {"age": 37, "savings": "8000000", "rate": "0.3200", "target": "0.37", "status": "short", "gap": "1250000", "surplus": None}


def test_meeting_the_rule_shows_the_margin():
    c = wealth_check(income=Decimal(30_000_000), expenses=Decimal(15_000_000), birth_year=1989, today=TODAY)
    assert c["status"] == "ok" and c["rate"] == "0.5000" and c["surplus"] == "3900000" and c["gap"] is None  # 15 tr vs 37% = 11,1 tr


def test_spending_all_income_has_no_savings():
    c = wealth_check(income=Decimal(20_000_000), expenses=Decimal(22_000_000), birth_year=1989, today=TODAY)
    assert c["status"] == "none" and c["savings"] == "-2000000" and c["gap"] == "9400000"  # 37% of 20 tr = 7,4 tr, plus the 2 tr overspend


def test_the_age_follows_the_year_and_the_target_is_capped():
    assert wealth_check(income=Decimal(1), expenses=Decimal(0), birth_year=1989, today=date(2027, 1, 2))["age"] == 38
    assert wealth_check(income=Decimal(10), expenses=Decimal(0), birth_year=1920, today=TODAY)["target"] == "0.90"  # a rule of thumb, not 106%
