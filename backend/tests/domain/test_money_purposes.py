from datetime import date
from decimal import Decimal as D

import pytest
from pydantic import ValidationError

from investment_agent.domain.deposit_book import DepositBook
from investment_agent.domain.money_purposes import MoneyPurposes, book_rows, purpose_view

TODAY = date(2026, 11, 9)
BOOK = DepositBook.model_validate({
    "accounts": [{"id": "a", "name": "TK con", "amount": "100000000", "liquid": True}],
    "deposits": [{"id": "d", "bank": "VCB", "matures": "2027-01-15", "principal": "300000000", "payout": "end", "locked": True}],
    "bonds": [{"id": "b", "name": "Quỹ", "amount": "50000000", "fund": "VFF", "units": "1000"}],
    "gold": [{"id": "g", "name": "Nhẫn", "amount": "40000000"}],
    "crypto": []})
QUOTES = {"funds": {"VFF": {"nav": "60000", "date": "2026-11-01"}}, "gold": {}}
PLAN = {"purposes": [{"id": "house", "name": "Quỹ mua nhà", "given": False}, {"id": "kid", "name": "Cho con", "given": True}], "tags": {"d": "house", "a": "kid", "gone": "kid"}}


def view(data=PLAN):
    return purpose_view(book_rows(BOOK, QUOTES, today=TODAY), MoneyPurposes.model_validate(data))


def test_each_row_of_the_book_is_listed_at_the_value_the_book_gives_it():
    rows = {r["id"]: r for r in book_rows(BOOK, QUOTES, today=TODAY)}
    assert (rows["a"]["kind"], rows["a"]["value"], rows["a"]["at_cost"]) == ("account", "100000000", False)
    assert rows["d"]["name"] == "VCB, đáo hạn 15/01/2027" and rows["d"]["value"] == "300000000"
    assert (rows["b"]["value"], rows["b"]["at_cost"]) == ("60000000", False)  # 1.000 đơn vị × NAV
    assert (rows["g"]["value"], rows["g"]["at_cost"]) == ("40000000", True)  # no price kind: what it cost


def test_purposes_add_up_and_what_is_given_away_comes_off_what_is_yours():
    v = view()
    by = {p["id"]: p for p in v["purposes"]}
    assert (by["house"]["total"], by["house"]["count"]) == ("300000000", 1)
    assert (by["kid"]["total"], by["kid"]["count"], by["kid"]["given"]) == ("100000000", 1, True)  # a tag on a row no longer in the book counts for nothing
    assert v["unassigned"] == {"total": "100000000", "count": 2}
    assert (v["total"], v["given_total"], v["mine_total"]) == ("500000000", "100000000", "400000000")


def test_with_nothing_tagged_everything_stays_unassigned():
    v = view({"purposes": [], "tags": {}})
    assert v["unassigned"]["count"] == 4 and v["given_total"] == "0" and v["mine_total"] == v["total"]


@pytest.mark.parametrize("bad", [{"purposes": [], "tags": {"a": "nope"}}, {"purposes": [{"id": "x", "name": "A", "given": False}, {"id": "x", "name": "B", "given": False}], "tags": {}},
                                 {"purposes": [{"id": "x", "name": " ", "given": False}], "tags": {}}])
def test_a_tag_needs_a_known_purpose_and_a_purpose_a_name_and_its_own_id(bad):
    with pytest.raises(ValidationError):
        MoneyPurposes.model_validate(bad)
