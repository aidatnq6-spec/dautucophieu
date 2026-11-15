from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.domain.deposit_book import DepositBook, bond_income, deposit_income, liquidity, maturity_calendar, maturity_ladder, totals

TODAY = date(2027, 1, 15)


def deposit(id, matures, principal="50000000", payout="end", interest=None, rate=None, locked=True, bank="Ngân hàng A"):
    return {"id": id, "bank": bank, "matures": matures, "principal": principal, "rate": rate, "interest": interest, "payout": payout,
            "locked": locked}


def book(deposits=(), accounts=()):
    return DepositBook.model_validate({"accounts": list(accounts), "deposits": list(deposits)})


def test_calendar_groups_by_month_and_counts_interest_only_when_paid_at_the_end_and_entered():
    b = book([deposit("a", "2027-03-05", interest="2000000"), deposit("b", "2027-03-20", payout="upfront", interest="2300000"),
              deposit("c", "2027-03-28"), deposit("d", "2027-05-03", principal="40000000", interest="1000000")])
    months = maturity_calendar(b, today=TODAY)["months"]
    assert months == [{"month": "2027-03", "count": 3, "principal": "150000000", "interest": "2000000", "missing_interest": 1},
                      {"month": "2027-05", "count": 1, "principal": "40000000", "interest": "1000000", "missing_interest": 0}]


def test_due_within_30_days_is_flagged_and_past_maturity_is_overdue_not_in_the_months():
    b = book([deposit("soon", "2027-02-14"), deposit("later", "2027-02-15"), deposit("old", "2027-01-14"), deposit("today", "2027-01-15")])
    cal = maturity_calendar(b, today=TODAY)
    assert cal["due_soon"] == ["today", "soon"] and cal["overdue"] == ["old"]
    assert [m["month"] for m in cal["months"]] == ["2027-01", "2027-02"] and cal["months"][1]["count"] == 2


def test_liquidity_counts_only_ledger_cash_and_accounts_marked_liquid():
    b = book([deposit("locked", "2027-03-01"), deposit("open", "2027-06-01", principal="30000000", locked=False), deposit("old", "2027-01-01", principal="20000000")],
             [{"id": "x", "name": "Tài khoản thanh toán", "amount": "10000000", "liquid": True},
              {"id": "y", "name": "Ví chưa rút", "amount": "5000000", "liquid": False}])
    l = liquidity(b, ledger_cash=Decimal("95000000"), reserve=Decimal("120000000"), today=TODAY)
    assert l["now"] == "105000000" and l["ledger_cash"] == "95000000" and l["accounts_liquid"] == "10000000"
    assert l["not_now"] == {"accounts": "5000000", "locked": "50000000", "unlocked": "30000000", "overdue": "20000000"}
    assert l["status"] == "short" and l["short"] == "15000000"
    assert l["maturing_90d"] == "50000000"  # 2027-03-01 is within 90 days; 2027-06-01 and the overdue one are not


def test_a_reserve_exactly_covered_is_enough():
    l = liquidity(book(), ledger_cash=Decimal("100"), reserve=Decimal("100"), today=TODAY)
    assert l["status"] == "enough" and l["short"] is None


def test_totals_are_the_principal_of_every_deposit_and_every_account():
    b = book([deposit("a", "2027-03-01"), deposit("old", "2027-01-01", principal="20000000")],
             [{"id": "x", "name": "TK", "amount": "10000000", "liquid": False}])
    t = totals(b, {})
    assert t["deposits"] == Decimal("70000000") and t["accounts"] == Decimal("10000000")


def test_income_uses_each_rate_and_the_market_rate_only_for_deposits_without_one():
    b = book([deposit("a", "2027-03-01", principal="120000000", rate="6"), deposit("b", "2027-04-01", principal="60000000")])
    assert deposit_income(b, market_rate=Decimal("5")) == {"monthly": Decimal("850000"), "market_rate_count": 1}  # 600.000 + 250.000


@pytest.mark.parametrize("bad", [
    {"deposits": [deposit("a", "2027-03-01", principal="0")]},
    {"deposits": [deposit("a", "2027-03-01", principal="1.5")]},
    {"deposits": [deposit("a", "2027-03-01", rate="31")]},
    {"deposits": [deposit("a", "2027-03-01"), deposit("a", "2027-04-01")]},
    {"deposits": [deposit("a", "2027-03-01", bank="")]},
    {"accounts": [{"id": "x", "name": "TK", "amount": "-1", "liquid": True}]},
    {"deposits": [deposit(str(i), "2027-03-01") for i in range(101)]},
])
def test_invalid_books_are_refused(bad):
    with pytest.raises(ValidationError):
        DepositBook.model_validate({"accounts": [], "deposits": [], **bad})


def test_when_the_owner_keeps_cash_to_the_book_the_ledger_cash_is_shown_but_not_counted():
    b = DepositBook.model_validate({"accounts": [{"id": "x", "name": "TK", "amount": "10000000", "liquid": True}], "deposits": [],
                                    "count_ledger_cash": False})
    l = liquidity(b, ledger_cash=Decimal("95000000"), reserve=Decimal("20000000"), today=TODAY)
    assert l["now"] == "10000000" and l["ledger_cash"] == "95000000" and l["ledger_cash_counted"] is False
    assert l["status"] == "short" and l["short"] == "10000000"
    assert book().count_ledger_cash is True  # the default keeps the ledger cash


def test_bonds_gold_and_crypto_are_listed_and_add_up_per_layer():
    b = DepositBook.model_validate({"bonds": [{"id": "vff", "name": "Quỹ trái phiếu A", "amount": "50000000", "rate": "7"},
                                              {"id": "dcbf", "name": "Quỹ trái phiếu B", "amount": "50200000", "rate": None}],
                                    "gold": [{"id": "pnj", "name": "Vàng nhẫn", "amount": "39364000"}],
                                    "crypto": [{"id": "btc", "name": "BTC", "amount": "1000000"}]})
    t = totals(b, {})
    assert t["bonds"] == Decimal("100200000") and t["gold"] == Decimal("39364000") and t["crypto"] == Decimal("1000000")


def test_bond_income_uses_each_rate_and_the_owner_bond_rate_for_rows_without_one():
    b = DepositBook.model_validate({"bonds": [{"id": "a", "name": "A", "amount": "120000000", "rate": "8"},
                                              {"id": "b", "name": "B", "amount": "60000000", "rate": None}]})
    assert bond_income(b, default_rate=Decimal("7"), navs={}) == {"monthly": Decimal("1150000"), "default_rate_count": 1}  # 800.000 + 350.000


@pytest.mark.parametrize("bad", [
    {"bonds": [{"id": "a", "name": "A", "amount": "-1", "rate": None}]},
    {"bonds": [{"id": "a", "name": "A", "amount": "1", "rate": "31"}]},
    {"gold": [{"id": "a", "name": "", "amount": "1"}]},
    {"crypto": [{"id": "a", "name": "BTC", "amount": "1.5"}]},
    {"gold": [{"id": "a", "name": "A", "amount": "1"}], "crypto": [{"id": "a", "name": "B", "amount": "1"}]},
])
def test_invalid_holdings_are_refused(bad):
    with pytest.raises(ValidationError):
        DepositBook.model_validate(bad)


# T6 Tiền theo kỳ hạn còn lại: the owner's cash and deposits by the time left to maturity, as a company's statements split them
# (under 3 months, 3 to 12 months, over 12 months), with what is locked in each.
def test_the_ladder_groups_by_time_left_to_maturity_and_keeps_overdue_and_locked_apart():
    b = book([deposit("a", "2027-04-15", principal="100000000"),                 # exactly three months: within 3 months
              deposit("b", "2027-04-16", principal="200000000", locked=False),   # a day later: 3 to 12 months
              deposit("c", "2028-01-15", principal="300000000"),                 # exactly twelve months
              deposit("d", "2028-01-16", principal="400000000"),                 # over twelve months
              deposit("e", "2027-01-10", principal="50000000")],                 # past its date
             [{"id": "x", "name": "Ví", "amount": "10000000", "liquid": True}, {"id": "y", "name": "Quỹ hưu", "amount": "40000000", "liquid": False}])
    lad = maturity_ladder(b, ledger_cash=Decimal("15000000"), today=TODAY)
    rows = {r["bucket"]: r for r in lad["rows"]}
    assert [r["bucket"] for r in lad["rows"]] == ["now", "within_3m", "3_12m", "over_12m", "overdue", "not_liquid"]
    assert (rows["now"]["amount"], rows["now"]["count"]) == ("25000000", 0)
    assert (rows["within_3m"]["amount"], rows["within_3m"]["count"], rows["within_3m"]["locked"]) == ("100000000", 1, "100000000")
    assert (rows["3_12m"]["amount"], rows["3_12m"]["count"], rows["3_12m"]["locked"]) == ("500000000", 2, "300000000")
    assert (rows["over_12m"]["amount"], rows["overdue"]["amount"], rows["not_liquid"]["amount"]) == ("400000000", "50000000", "40000000")
    assert lad["total"] == "1115000000" and rows["3_12m"]["share"] == "0.4484"
    # the statements' "tiền và tương đương tiền": cash now and what comes back within three months
    assert lad["cash_equivalent"] == "125000000"


def test_the_ladder_of_an_empty_book_is_the_ledger_cash_or_nothing():
    lad = maturity_ladder(book(), ledger_cash=Decimal(0), today=TODAY)
    assert lad["total"] == "0" and all(r["share"] is None for r in lad["rows"])
    kept = DepositBook.model_validate({"count_ledger_cash": False})
    assert maturity_ladder(kept, ledger_cash=Decimal("9"), today=TODAY)["rows"][0]["amount"] == "0"  # the ledger's cash is not counted
