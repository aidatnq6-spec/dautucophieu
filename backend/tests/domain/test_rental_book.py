from datetime import date

import pytest
from pydantic import ValidationError

from investment_agent.domain.rental_book import RentalBook, book_view, due_items

TODAY = date(2026, 11, 10)
U301 = {"id": "u1", "name": "301", "tenant": "Khách A", "rent": "7000000", "due_day": 8, "start": "2026-09-01", "ends": "2026-12-01", "deposit": "7000000", "broker": "Môi giới A", "commission": "3500000"}
U302 = {"id": "u2", "name": "302", "tenant": "Khách B", "rent": "6500000", "due_day": 15, "start": "2026-11-01"}
U201 = {"id": "u3", "name": "201", "rent": "6000000", "due_day": 5}
PAID = [{"id": "p1", "unit": "u1", "month": "2026-09", "amount": "7000000", "paid_on": "2026-09-08"}, {"id": "p2", "unit": "u1", "month": "2026-10", "amount": "3000000", "paid_on": "2026-10-09"}]


def book(units=(U301, U302, U201), payments=PAID):
    return RentalBook.model_validate({"units": list(units), "payments": list(payments)})


def units(b=None):
    return {u["id"]: u for u in book_view(b or book(), today=TODAY)["units"]}


def test_each_month_since_the_lease_began_is_paid_short_or_unpaid_and_the_debt_adds_up():
    u = units()["u1"]
    assert [(m["month"], m["status"], m["owed"]) for m in u["months"]] == [("2026-09", "paid", "0"), ("2026-10", "short", "4000000"), ("2026-11", "unpaid", "7000000")]
    assert u["owed"] == "11000000" and u["lease_days_left"] == 21


def test_this_month_before_its_day_is_still_waiting():
    assert [(m["month"], m["status"]) for m in units()["u2"]["months"]] == [("2026-11", "pending")]
    assert units()["u2"]["owed"] == "0"


def test_a_room_without_a_tenant_is_vacant_and_owes_nothing():
    u = units()["u3"]
    assert u["vacant"] is True and u["months"] == [] and u["owed"] == "0"


def test_the_book_totals_rent_collected_this_year_deposits_and_vacancy():
    t = book_view(book(), today=TODAY)["totals"]
    assert (t["rent_monthly"], t["collected_year"], t["owed"], t["deposits"], t["occupied"], t["vacant"]) == ("13500000", "10000000", "11000000", "7000000", 2, 1)


def test_months_after_the_lease_ends_are_not_owed():
    ended = {**U301, "ends": "2026-10-15"}
    assert [m["month"] for m in units(book(units=(ended,)))["u1"]["months"]] == ["2026-09", "2026-10"]


def test_reminders_for_rent_past_its_day_and_a_lease_ending_within_thirty_days():
    items = due_items(book(), TODAY)
    assert [(k, line) for k, _, line in items] == [
        ("rent_due", "Phòng 301: chưa thu đủ tiền thuê tháng 11/2026 (hạn 08/11/2026), còn thiếu 7.000.000 đ"),
        ("lease_end", "Phòng 301: hợp đồng hết hạn 01/12/2026, còn 21 ngày")]
    assert [k for k, _, _ in due_items(book(), date(2026, 11, 7))] == ["lease_end"]  # before the rent day


def test_a_short_day_of_the_month_uses_the_last_day():
    b = book(units=({**U302, "due_day": 31, "start": "2026-02-01"},), payments=())
    feb = units(b)["u2"]["months"][0]
    assert feb["due_on"] == "2026-02-28"


@pytest.mark.parametrize("bad", [
    {"units": [{**U301, "due_day": 32}], "payments": []},
    {"units": [U301, {**U302, "name": "301"}], "payments": []},
    {"units": [U301], "payments": [{**PAID[0], "unit": "x"}]},
    {"units": [U301], "payments": [{**PAID[0], "amount": "0"}]},
    {"units": [U301], "payments": [{**PAID[0], "month": "2026-13"}]}])
def test_bad_rows_are_refused(bad):
    with pytest.raises(ValidationError):
        RentalBook.model_validate(bad)


def test_months_before_the_book_began_tracking_are_not_owed():
    """Rent received before the room was entered here sits in the owner's spreadsheet: an unrecorded month is not an unpaid one."""
    tracked = {**U301, "track_from": "2026-11"}
    u = units(book(units=(tracked,), payments=()))["u1"]
    assert [(m["month"], m["status"]) for m in u["months"]] == [("2026-11", "unpaid")] and u["owed"] == "7000000"
    later = {**U301, "start": "2026-11-05", "track_from": "2026-09"}  # the lease starts later than tracking: the lease wins
    assert [m["month"] for m in units(book(units=(later,), payments=()))["u1"]["months"]] == ["2026-11"]


def test_a_bad_tracking_month_is_refused():
    with pytest.raises(ValidationError):
        RentalBook.model_validate({"units": [{**U301, "track_from": "2026-13"}], "payments": []})
