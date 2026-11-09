from datetime import date
from decimal import Decimal as D

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.domain.accumulation import Buy, Plan, PostRefused, book_targets, post_to_book
from investment_agent.domain.deposit_book import DepositBook
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository, VersionConflict

OWNER = OwnerContext("owner-1", "owner", "test")
GOLD = Plan.model_validate({"id": "g", "name": "Vàng nhẫn", "asset": "gold", "day": 10, "start": "2026-09", "chi": "1", "kind": "Nhẫn"})
FUND = Plan.model_validate({"id": "f", "name": "Quỹ VFF", "asset": "fund", "day": 5, "start": "2026-10", "amount": "13000000", "fund": "VFF"})
BUY = Buy.model_validate({"id": "1", "plan": "g", "on": "2026-09-12", "amount": "12000000", "quantity": "1.5"})
FUND_BUY = Buy.model_validate({"id": "2", "plan": "f", "on": "2026-10-06", "amount": "13000000", "quantity": "500.25"})
BOOK = DepositBook.model_validate({"gold": [{"id": "r", "name": "Nhẫn", "amount": "50000000", "kind": "Nhẫn", "chi": "5"}, {"id": "s", "name": "Khác", "amount": "1000000", "kind": "SJC", "chi": "1"}, {"id": "c", "name": "Theo vốn", "amount": "9000000"}],
                                   "bonds": [{"id": "v", "name": "VFF", "amount": "26000000", "fund": "VFF", "units": "1000", "rate": "8"}, {"id": "t", "name": "Trái phiếu", "amount": "5000000"}], "reserve": "7000000", "count_ledger_cash": False})


def test_a_buy_is_added_to_the_gold_row_in_money_and_chi_and_the_rest_of_the_book_stays():
    new, row = post_to_book(BOOK, GOLD, BUY, "r", new_id="n")
    assert row == "r" and (new.gold[0].amount, new.gold[0].chi) == (D("62000000"), D("6.5"))
    assert new.gold[1] == BOOK.gold[1] and new.bonds == BOOK.bonds and new.reserve == D("7000000") and new.count_ledger_cash is False


def test_a_buy_is_added_to_the_fund_row_in_money_and_units_keeping_its_rate():
    new, _ = post_to_book(BOOK, FUND, FUND_BUY, "v", new_id="n")
    assert (new.bonds[0].amount, new.bonds[0].units, new.bonds[0].rate) == (D("39000000"), D("1500.25"), D("8"))


def test_no_row_chosen_makes_a_new_one_named_after_the_plan():
    new, row = post_to_book(BOOK, GOLD, BUY, None, new_id="n")
    assert row == "n" and (new.gold[-1].name, new.gold[-1].amount, new.gold[-1].kind, new.gold[-1].chi) == ("Vàng nhẫn", D("12000000"), "Nhẫn", D("1.5"))
    new, _ = post_to_book(BOOK, FUND, FUND_BUY, None, new_id="n")
    assert (new.bonds[-1].fund, new.bonds[-1].units) == ("VFF", D("500.25"))


def test_only_rows_priced_the_same_way_can_take_the_buy():
    assert [r["id"] for r in book_targets(BOOK, GOLD)] == ["r"]
    assert [r["id"] for r in book_targets(BOOK, FUND)] == ["v"]
    for row in ("s", "c", "v", "missing"):
        with pytest.raises(PostRefused):
            post_to_book(BOOK, GOLD, BUY, row, new_id="n")


def test_a_quantity_the_book_cannot_hold_is_refused_rather_than_rounded():
    fine = Buy.model_validate({"id": "1", "plan": "g", "on": "2026-09-12", "amount": "12000000", "quantity": "0.125"})
    with pytest.raises(PostRefused):
        post_to_book(BOOK, GOLD, fine, "r", new_id="n")


def test_a_full_list_is_refused():
    full = DepositBook.model_validate({"gold": [{"id": f"x{i}", "name": "V", "amount": "1"} for i in range(30)]})
    with pytest.raises(PostRefused):
        post_to_book(full, GOLD, BUY, None, new_id="n")


def repo():
    r = PersonalRepository("owner-1", MemoryDocumentStore())
    r.write(OWNER, "settings", "a", {"n": 1}, expected_version=0, request_id="a1")
    r.write(OWNER, "settings", "b", {"n": 1}, expected_version=0, request_id="b1")
    return r


def test_two_records_are_written_together():
    r = repo()
    assert r.write_many(OWNER, [("settings", "a", {"n": 2}, 1), ("settings", "b", {"n": 2}, 1)], request_id="m1") == [2, 2]
    assert r.read(OWNER, "settings", "a").payload == {"n": 2} and r.read(OWNER, "settings", "b").payload == {"n": 2}
    assert r.write_many(OWNER, [("settings", "a", {"n": 2}, 1), ("settings", "b", {"n": 2}, 1)], request_id="m1") == [2, 2]  # a retry changes nothing
    assert r.read(OWNER, "settings", "a").version == 2


def test_if_either_record_has_moved_neither_is_written():
    r = repo()
    with pytest.raises(VersionConflict):
        r.write_many(OWNER, [("settings", "a", {"n": 2}, 1), ("settings", "b", {"n": 2}, 9)], request_id="m2")
    assert r.read(OWNER, "settings", "a").version == 1 and r.read(OWNER, "settings", "b").version == 1
