from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.domain.deposit_book import DepositBook, gold_values, totals

RING = "Nhẫn tròn Phú Quý 999.9"
GOLD = {"source": "Phú Quý", "unit": "chỉ", "as_of": "2026-11-06T18:28:00+07:00", "kinds": {RING: {"buy": "13650000", "sell": "14050000"}}}


def book(*rows):
    return DepositBook.model_validate({"gold": list(rows)})


def row(id, amount="39364000", **more):
    return {"id": id, "name": f"Vàng {id}", "amount": amount, **more}


def test_a_gold_row_is_worth_its_chi_times_the_buying_price_per_chi():
    b = book(row("a", kind=RING, chi="3"), row("b"), row("c", kind="Loại đã bỏ", chi="1"))
    rows = gold_values(b, GOLD, today=date(2026, 11, 6))
    assert rows[0] == {"id": "a", "cost": "39364000", "value": "40950000", "source": "price", "kind": RING, "buy_per_chi": "13650000",
                       "as_of": "2026-11-06T18:28:00+07:00", "stale": False, "change": "1586000"}  # 3 × 13.650.000
    assert rows[1] == {"id": "b", "cost": "39364000", "value": "39364000", "source": "amount"}
    assert rows[2] == {"id": "c", "cost": "39364000", "value": "39364000", "source": "no_price", "kind": "Loại đã bỏ"}
    assert gold_values(b, GOLD, today=date(2026, 11, 10))[0]["stale"] is True  # more than 3 days old
    assert totals(b, {"gold": GOLD})["gold"] == Decimal("40950000") + Decimal("39364000") * 2
    assert totals(b, {})["gold"] == Decimal("39364000") * 3  # no prices yet: at cost


def test_a_kind_needs_its_chi_and_chi_has_at_most_two_decimals():
    for bad in ({"kind": RING}, {"chi": "1"}, {"kind": RING, "chi": "0"}, {"kind": RING, "chi": "1.255"}):
        with pytest.raises(ValidationError):
            book(row("a", **bad))
    assert book(row("a", kind=RING, chi="1.25")).gold[0].chi == Decimal("1.25")
