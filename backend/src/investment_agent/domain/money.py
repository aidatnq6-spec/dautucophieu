"""Exact decimal parsing at JSON boundaries.

Keep full Decimal precision for calculations and cost allocation. Round only
for display with ROUND_HALF_UP at the display unit (usually whole VND).
Cash reconciliation must use unrounded ledger amounts; allocate residual cost
to the final lot so the sum of allocated costs equals the original total.
"""

import re
from decimal import Decimal


_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


def parse_amount(value: str, *, allow_negative: bool = False) -> Decimal:
    """Parse a canonical decimal JSON string without binary-float conversion."""
    if not isinstance(value, str):
        raise ValueError("amount must be a decimal string")
    if not _DECIMAL.fullmatch(value):
        raise ValueError("amount must be a finite plain decimal string")
    result = Decimal(value)
    if value.startswith("-") and not allow_negative:
        raise ValueError("amount must be nonnegative")
    return result


def parse_ratio(value: str) -> Decimal:
    """Parse a decimal JSON string in the inclusive interval [0, 1]."""
    result = parse_amount(value)
    if result > 1:
        raise ValueError("ratio must be between 0 and 1")
    return result
