from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.domain.property_book import Policy, PropertyBook, next_due, picture

TODAY = date(2026, 11, 9)
HOME = {"id": "a", "name": "Nhà A", "kind": "home", "purpose": "live", "value": "5000000000", "valued_on": "2026-10-01", "legal": "certificate"}
LIFE = {"id": "p", "name": "Nhân thọ A", "insurer": "Công ty A", "insured": "Người A", "kind": "life", "premium": "20000000", "frequency": "year", "due_on": "2026-06-16",
        "account_value": "52000000", "valued_on": "2026-06-16"}
HOUSE = {"id": "h", "name": "Bảo hiểm nhà", "kind": "property", "premium": "3000000", "frequency": "year", "due_on": "2026-05-05"}


def book(*policies, properties=(HOME,)):
    return PropertyBook.model_validate({"properties": list(properties), "policies": list(policies)})


def policy(**over):
    return Policy.model_validate({**LIFE, **over})


def test_the_next_premium_follows_the_period_from_any_due_date():
    assert next_due(Policy.model_validate(HOUSE), TODAY) == date(2027, 5, 5)
    assert next_due(policy(due_on="2026-11-09"), TODAY) == date(2026, 11, 9)  # due today
    assert next_due(policy(frequency="quarter", due_on="2026-02-10"), TODAY) == date(2026, 11, 10)
    assert next_due(policy(frequency="month", due_on="2026-01-31"), TODAY) == date(2026, 11, 30)  # a short month keeps its last day
    assert next_due(policy(frequency="half", due_on="2029-03-01"), TODAY) == date(2027, 3, 1)  # March and September: a later date given works backwards too


def test_no_due_date_or_a_matured_policy_has_no_next_premium():
    assert next_due(policy(due_on=None), TODAY) is None
    assert next_due(policy(matures="2027-01-01"), TODAY) is None  # the next one would be after it ends


def test_a_life_policy_counts_at_its_surrender_value_or_else_its_account_value_named_as_such():
    p = picture(book(LIFE, HOUSE), financial=Decimal("1000000000"), today=TODAY)
    assert (p["insurance"], p["insurance_at_account"], p["insurance_missing"]) == ("52000000", ["Nhân thọ A"], [])
    assert p["total_assets"] == "6052000000" and p["insurance_share"] == "0.0086"
    p = picture(book({**LIFE, "surrender_value": "40000000"}), financial=Decimal("1000000000"), today=TODAY)
    assert (p["insurance"], p["insurance_at_account"]) == ("40000000", [])


def test_a_life_policy_without_a_value_stops_the_totals_and_is_named():
    p = picture(book({**LIFE, "account_value": None}), financial=Decimal("1000000000"), today=TODAY)
    assert p["complete"] is False and p["insurance_missing"] == ["Nhân thọ A"] and p["net_worth"] is None


def test_premiums_add_up_for_a_year_and_a_missing_one_is_named():
    p = picture(book(LIFE, HOUSE, {**HOUSE, "id": "m", "name": "Sức khỏe", "kind": "health", "premium": "1000000", "frequency": "month"}, {**HOUSE, "id": "x", "name": "Chưa rõ phí", "premium": None}),
                financial=None, today=TODAY)
    assert p["premiums_yearly"] == "35000000" and p["premiums_missing"] == ["Chưa rõ phí"]
    assert p["policy_due"]["h"] == "2027-05-05"


def test_an_old_value_is_flagged():
    assert picture(book(LIFE), financial=None, today=TODAY)["insurance_stale"] == []  # 146 days
    assert picture(book({**LIFE, "valued_on": "2026-04-01"}), financial=None, today=TODAY)["insurance_stale"] == ["Nhân thọ A"]


def test_the_split_counts_insurance_with_what_is_invested():
    p = picture(book(LIFE), financial=Decimal("1000000000"), today=TODAY)
    assert p["invest_total"] == "1052000000" and p["insurance_of_invest"] == "0.0494"


@pytest.mark.parametrize("bad", [{**HOUSE, "account_value": "1000"}, {**LIFE, "premium": "1000.5"}, {**LIFE, "frequency": "week"}])
def test_only_life_cover_holds_a_value_and_amounts_are_whole(bad):
    with pytest.raises(ValidationError):
        book(bad)


def test_ids_stay_unique_across_the_book():
    with pytest.raises(ValidationError):
        book({**LIFE, "id": "a"})
