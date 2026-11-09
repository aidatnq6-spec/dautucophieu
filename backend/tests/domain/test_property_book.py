from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.domain.property_book import Loan, Property, PropertyBook, loan_payment, picture

TODAY = date(2026, 11, 9)
HOME = {"id": "a", "name": "Nhà A", "kind": "home", "purpose": "rent", "value": "5000000000", "valued_on": "2026-10-01", "legal": "certificate", "rent_monthly": "10000000"}
LAND = {"id": "b", "name": "Đất B", "kind": "land", "purpose": "invest", "value": "1000000000", "valued_on": "2026-01-01", "legal": "unknown"}
LOAN = {"id": "l", "name": "Vay nhà", "balance": "1200000000", "rate": "12", "months_left": 120, "method": "declining", "collateral": "a"}


def book(properties=(HOME, LAND), loans=(LOAN,), **more):
    return PropertyBook.model_validate({"properties": list(properties), "loans": list(loans), **more})


def test_a_declining_loan_pays_equal_principal_and_this_months_interest():
    assert loan_payment(Loan.model_validate(LOAN)) == Decimal("22000000")  # 1,2 tỷ / 120 + 1,2 tỷ × 12% / 12


def test_a_level_loan_pays_the_annuity_and_a_free_one_divides_the_balance():
    level = {"id": "x", "name": "V", "balance": "1000000", "rate": "12", "months_left": 12, "method": "annuity"}
    assert loan_payment(Loan.model_validate(level)) == Decimal("88849")
    assert loan_payment(Loan.model_validate({**level, "balance": "1200", "rate": "0"})) == Decimal("100")


@pytest.mark.parametrize("missing", ["balance", "rate", "months_left"])
def test_a_payment_needs_all_its_figures(missing):
    assert loan_payment(Loan.model_validate({**LOAN, missing: None})) is None


def test_the_whole_picture_adds_up_with_financial_assets_property_and_debt():
    p = picture(book(), financial=Decimal("2000000000"), today=TODAY)
    assert p["complete"] is True
    assert (p["total_assets"], p["net_worth"], p["debt"], p["payments"], p["rent"]) == ("8000000000", "6800000000", "1200000000", "22000000", "10000000")
    assert (p["liquid_share"], p["clear_share"], p["unclear_share"], p["property_share"], p["debt_ratio"]) == ("0.2500", "0.6250", "0.1250", "0.7500", "0.1500")
    assert p["rent_less_payments"] == "-12000000"
    assert p["loans"] == {"l": "22000000"}


def test_property_above_the_ceiling_is_flagged_and_the_ceiling_can_be_moved():
    assert picture(book(), financial=Decimal("2000000000"), today=TODAY)["over"] is True  # 75% against the default 70%
    assert picture(book(ceiling="80"), financial=Decimal("2000000000"), today=TODAY)["over"] is False


def test_a_value_older_than_six_months_or_with_no_date_is_named():
    undated = {**HOME, "valued_on": None}
    assert picture(book(), financial=Decimal("1"), today=TODAY)["stale"] == ["Đất B"]
    assert picture(book(properties=[undated]), financial=Decimal("1"), today=TODAY)["stale"] == ["Nhà A"]
    fresh = {**LAND, "valued_on": "2026-05-13"}  # 180 days before: still within
    assert picture(book(properties=[fresh], loans=[]), financial=Decimal("1"), today=TODAY)["stale"] == []


@pytest.mark.parametrize("change, named", [({"properties": [{**HOME, "value": None}, LAND]}, ("property_missing", "Nhà A")),
                                           ({"loans": [{**LOAN, "balance": None}]}, ("debt_missing", "Vay nhà"))])
def test_a_blank_value_or_balance_is_named_and_no_net_worth_is_given(change, named):
    p = picture(book(**change) if "properties" in change and "loans" in change else book(properties=change.get("properties", (HOME, LAND)), loans=change.get("loans", (LOAN,))),
                financial=Decimal("2000000000"), today=TODAY)
    assert p["complete"] is False and p["net_worth"] is None and p["total_assets"] is None and p["property_share"] is None and p["over"] is False
    assert p[named[0]] == [named[1]]


def test_without_financial_assets_there_is_no_total_but_debt_and_payments_are_still_shown():
    p = picture(book(), financial=None, today=TODAY)
    assert p["net_worth"] is None and p["complete"] is False
    assert p["debt"] == "1200000000" and p["payments"] == "22000000" and p["property_total"] == "6000000000"


def test_a_loan_missing_what_its_payment_needs_is_named_and_rent_is_not_compared():
    p = picture(book(loans=[{**LOAN, "rate": None}]), financial=Decimal("1"), today=TODAY)
    assert p["payments_missing"] == ["Vay nhà"] and p["rent_less_payments"] is None and p["loans"] == {"l": None}


def test_an_empty_book_is_just_the_financial_assets():
    p = picture(PropertyBook(), financial=Decimal("500"), today=TODAY)
    assert p["net_worth"] == "500" and p["liquid_share"] == "1.0000" and p["over"] is False


def test_nothing_at_all_has_no_shares():
    p = picture(PropertyBook(), financial=Decimal("0"), today=TODAY)
    assert p["net_worth"] == "0" and p["liquid_share"] is None and p["debt_ratio"] is None


@pytest.mark.parametrize("bad", [{"properties": [HOME, HOME]}, {"loans": [{**LOAN, "collateral": "nope"}], "properties": [HOME]}, {"ceiling": "0"}, {"ceiling": "101"},
                                 {"properties": [{**HOME, "value": "1.5"}]}, {"loans": [{**LOAN, "months_left": 0}], "properties": [HOME]}, {"loans": [{**LOAN, "rate": "101"}], "properties": [HOME]}])
def test_the_book_refuses_what_cannot_be_right(bad):
    with pytest.raises(ValidationError):
        PropertyBook.model_validate(bad)


def test_a_property_needs_only_its_name_and_choices():
    assert Property.model_validate({"id": "z", "name": "Nhà", "kind": "other", "purpose": "live", "legal": "unknown"}).value is None


LIVE = {"id": "c", "name": "Nhà ở", "kind": "home", "purpose": "live", "value": "4000000000", "valued_on": "2026-10-01", "legal": "certificate"}


def test_assets_are_split_into_what_is_lived_in_and_what_is_invested():
    p = picture(book(properties=(HOME, LAND, LIVE), loans=()), financial=Decimal("2000000000"), today=TODAY)
    assert (p["live_total"], p["invest_total"], p["invest_property_total"]) == ("4000000000", "8000000000", "6000000000")
    assert (p["live_share"], p["invest_share"], p["invest_property_of_invest"], p["financial_of_invest"]) == ("0.3333", "0.6667", "0.7500", "0.2500")


def test_the_split_waits_for_every_value():
    p = picture(book(properties=(HOME, {**LIVE, "value": None}), loans=()), financial=Decimal("2000000000"), today=TODAY)
    assert p["live_total"] is None and p["invest_total"] is None and p["live_share"] is None


def test_rental_yield_is_given_per_property_only_with_both_figures():
    p = picture(book(properties=(HOME, LAND, {**LIVE, "value": None, "rent_monthly": "1000000"}), loans=()), financial=None, today=TODAY)
    assert p["yields"] == {"a": "0.0240", "b": None, "c": None}  # 10 tr × 12 / 5 tỷ


def test_rent_counts_what_is_entered_and_names_a_let_property_without_one():
    from investment_agent.domain.property_book import rent_now
    assert rent_now(book(properties=(HOME, {**HOME, "id": "z", "name": "Căn Z", "rent_monthly": None}, LIVE), loans=())) == (Decimal("10000000"), ["Căn Z"])
