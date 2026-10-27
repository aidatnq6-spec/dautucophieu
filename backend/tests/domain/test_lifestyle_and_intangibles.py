from datetime import date
from decimal import Decimal

from investment_agent.domain.intangibles import intangibles_year
from investment_agent.domain.lifestyle import lifestyle_inflation

TODAY = date(2027, 10, 20)


def month(income, expenses):
    return {"income": str(income), "expenses": str(expenses)}


def test_spending_growing_faster_than_income_is_lifestyle_inflation():
    history = {"2026-10": month(28_000_000, 17_000_000), "2027-04": month(29_000_000, 18_500_000), "2027-10": month(30_000_000, 20_000_000)}
    r = lifestyle_inflation(history, cpi="3.2", today=TODAY)
    assert r["from"] == "2026-10" and r["to"] == "2027-10" and r["months"] == 12
    assert r["spending_change"] == "0.1765" and r["income_change"] == "0.0714" and r["verdict"] == "faster_than_income"


def test_spending_between_inflation_and_income_and_spending_below_income_growth():
    faster_than_cpi = {"2027-04": month(20_000_000, 10_000_000), "2027-10": month(24_000_000, 11_000_000)}   # +10% spending, +20% income
    assert lifestyle_inflation(faster_than_cpi, cpi="3.2", today=TODAY)["verdict"] == "faster_than_inflation"
    fine = {"2027-04": month(20_000_000, 10_000_000), "2027-10": month(24_000_000, 10_200_000)}               # +2% spending
    assert lifestyle_inflation(fine, cpi="3.2", today=TODAY)["verdict"] == "ok"
    no_cpi = lifestyle_inflation(fine, cpi=None, today=TODAY)
    assert no_cpi["verdict"] == "ok" and no_cpi["cpi"] is None


def test_the_comparison_needs_six_months_and_prefers_twelve():
    early = lifestyle_inflation({"2027-08": month(30_000_000, 20_000_000), "2027-10": month(30_000_000, 21_000_000)}, cpi="3.2", today=TODAY)
    assert early["verdict"] is None and early["ready_on"] == "2028-02"
    both = {"2026-08": month(1, 1), "2026-10": month(28_000_000, 17_000_000), "2027-03": month(1, 1), "2027-10": month(30_000_000, 20_000_000)}
    assert lifestyle_inflation(both, cpi=None, today=TODAY)["from"] == "2026-10"  # the same month a year earlier when stored
    assert lifestyle_inflation({}, cpi=None, today=TODAY)["verdict"] is None


def test_intangible_spending_this_year_against_a_share_of_yearly_income():
    entries = [{"on": "2026-12-01", "amount": "4000000"}, {"on": "2027-02-10", "amount": "5000000"}, {"on": "2027-09-01", "amount": "1500000"},
               {"on": "2027-09-05", "amount": "-500000"}]  # an adjustment line
    r = intangibles_year(entries, monthly_income=Decimal(30_000_000), target_rate=Decimal("10"), today=TODAY)
    assert r == {"year": 2027, "spent": "6000000", "target": "36000000", "progress": "0.1667"}
    assert intangibles_year([], monthly_income=None, target_rate=Decimal("10"), today=TODAY) == {"year": 2027, "spent": "0", "target": None, "progress": None}
