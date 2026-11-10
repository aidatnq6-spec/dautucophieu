from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.domain.property_book import PropertyBook, picture

TODAY = date(2026, 11, 9)
HOME = {"id": "a", "name": "Nhà A", "kind": "home", "purpose": "live", "value": "5000000000", "valued_on": "2026-10-01", "legal": "certificate"}
HOLIDAY = {"id": "v1", "name": "Gói kỳ nghỉ", "kind": "holiday_right", "contributed": "86300000", "papers": "none", "annual_fee": "6000000", "fee_due": "2026-03-01", "ends": "2045-03-01"}
RENT = {"id": "v2", "name": "Tòa nhà A", "kind": "rent_share", "partners": "Đối tác", "contributed": "50000000", "papers": "none"}
RESORT = {"id": "v3", "name": "Căn nghỉ dưỡng", "kind": "resort", "contributed": "10000000", "value": "12000000", "valued_on": "2026-10-01", "papers": "handwritten"}


def book(*ventures):
    return PropertyBook.model_validate({"properties": [HOME], "ventures": list(ventures)})


def pic(*ventures, financial="1000000000"):
    return picture(book(*ventures), financial=Decimal(financial) if financial else None, today=TODAY)


def test_a_share_counts_at_its_estimate_or_else_at_what_was_put_in_named_as_such():
    p = pic(HOLIDAY, RENT, RESORT)
    assert (p["ventures"], p["ventures_at_cost"], p["ventures_missing"]) == ("62000000", ["Tòa nhà A"], [])
    assert p["total_assets"] == "6062000000" and p["ventures_share"] == "0.0102"


def test_a_holiday_right_is_left_out_unless_the_owner_values_it():
    assert pic(HOLIDAY)["ventures_excluded"] == ["Gói kỳ nghỉ"] and pic(HOLIDAY)["ventures"] == "0"
    p = pic({**HOLIDAY, "value": "20000000", "valued_on": "2026-10-01"})
    assert p["ventures"] == "20000000" and p["ventures_excluded"] == []


def test_shares_in_property_count_towards_the_property_ceiling_and_without_notarised_papers_as_unclear():
    p = pic(HOLIDAY, RENT, RESORT)
    assert (p["property_share"], p["clear_share"], p["unclear_share"]) == ("0.8350", "0.8248", "0.0102")
    assert p["ventures_unpapered"] == ["Gói kỳ nghỉ", "Tòa nhà A", "Căn nghỉ dưỡng"]
    assert pic({**RENT, "papers": "notarized"})["ventures_unpapered"] == []


def test_the_split_counts_shares_with_what_is_invested():
    assert pic(HOLIDAY, RENT, RESORT)["ventures_of_invest"] == "0.0584"


def test_a_share_with_no_figure_at_all_stops_the_totals_and_is_named():
    p = pic({**RENT, "contributed": None})
    assert p["complete"] is False and p["ventures_missing"] == ["Tòa nhà A"] and p["net_worth"] is None


def test_yearly_fees_their_next_date_and_an_ended_right():
    p = pic(HOLIDAY, financial=None)
    assert p["venture_fees_yearly"] == "6000000" and p["venture_due"]["v1"] == "2027-03-01"
    assert pic({**HOLIDAY, "ends": "2026-01-01"}, financial=None)["venture_due"]["v1"] is None


def test_an_old_estimate_is_flagged_but_a_figure_at_cost_is_not():
    assert pic(RENT, RESORT)["ventures_stale"] == []
    assert pic({**RESORT, "valued_on": "2026-04-01"})["ventures_stale"] == ["Căn nghỉ dưỡng"]


@pytest.mark.parametrize("bad", [{**RENT, "share": "0"}, {**RENT, "share": "101"}, {**RENT, "contributed": "1.5"}, {**RENT, "papers": "maybe"}, {**RENT, "id": "a"}])
def test_bad_rows_are_refused(bad):
    with pytest.raises(ValidationError):
        book(bad)
