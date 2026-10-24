from decimal import Decimal

import pytest

from investment_agent.domain.money import parse_amount, parse_ratio


def test_money_roundtrip_preserves_fractional_precision():
    value = parse_amount("100000000.125")
    assert value == Decimal("100000000.125")
    assert parse_amount(str(value)) == value


@pytest.mark.parametrize("value", [1.25, Decimal("1.25"), 1, "NaN", "Infinity", "1e3", " 1", "", "01"])
def test_money_rejects_noncanonical_or_nonstring_input(value):
    with pytest.raises((TypeError, ValueError)):
        parse_amount(value)


def test_negative_money_requires_explicit_permission():
    with pytest.raises(ValueError):
        parse_amount("-0.01")
    assert parse_amount("-0.01", allow_negative=True) == Decimal("-0.01")


@pytest.mark.parametrize("value", ["0", "0.25", "1", "1.000"])
def test_ratio_inclusive_boundaries(value):
    assert parse_ratio(value) == Decimal(value)


@pytest.mark.parametrize("value", ["-0.01", "1.0001", "2", 0.5])
def test_ratio_rejects_out_of_range_or_nonstring(value):
    with pytest.raises((TypeError, ValueError)):
        parse_ratio(value)
