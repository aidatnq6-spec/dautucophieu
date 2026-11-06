from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.domain.deposit_book import DepositBook, bond_income, bond_values, totals

NAVS = {"VFF": {"name": "Quỹ A", "nav": "27214.48", "date": "2026-11-05"}, "OLD": {"name": "Quỹ B", "nav": "10000", "date": "2026-10-20"}}


def book(*bonds):
    return DepositBook.model_validate({"bonds": list(bonds)})


def bond(id, amount="50000000", **more):
    return {"id": id, "name": f"Quỹ {id}", "amount": amount, "rate": None, **more}


def test_a_fund_row_is_worth_its_units_times_the_latest_nav_and_shows_the_change_from_what_it_cost():
    b = book(bond("a", fund="VFF", units="1900.55"), bond("b"), bond("c", fund="NONE", units="10"), bond("d", fund="OLD", units="5000", rate="6"))
    rows = bond_values(b, NAVS, today=date(2026, 11, 6))
    assert rows[0] == {"id": "a", "cost": "50000000", "value": "51722480", "source": "nav", "fund": "VFF", "nav": "27214.48",
                       "nav_date": "2026-11-05", "stale": False, "change": "1722480"}  # 1900.55 × 27214.48 = 51722479.964
    assert rows[1] == {"id": "b", "cost": "50000000", "value": "50000000", "source": "amount"}
    assert rows[2] == {"id": "c", "cost": "50000000", "value": "50000000", "source": "no_nav", "fund": "NONE"}  # never a guessed NAV
    assert rows[3]["stale"] is True and rows[3]["value"] == "50000000"  # NAV of 20/10 is more than 14 days old
    assert totals(b, NAVS)["bonds"] == Decimal("201722480")
    assert bond_income(b, default_rate=Decimal("7"), navs=NAVS)["monthly"] == (Decimal("51722480") * 7 + Decimal("100000000") * 7
                                                                             + Decimal("50000000") * 6) / 100 / 12


def test_a_fund_code_needs_units_and_units_need_a_code_with_at_most_two_decimals():
    for bad in ({"fund": "VFF"}, {"units": "10"}, {"fund": "VFF", "units": "1.234"}, {"fund": "VFF", "units": "0"}, {"fund": "vff!", "units": "1"}):
        with pytest.raises(ValidationError):
            book(bond("a", **bad))
    assert book(bond("a", fund="VFF", units="1.5")).bonds[0].units == Decimal("1.5")
    assert book(bond("a", fund="VCBF-FIF", units="2")).bonds[0].fund == "VCBF-FIF"  # Fmarket codes may carry a hyphen
