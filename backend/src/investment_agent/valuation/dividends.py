"""Dividend discount model: total expected dividends to parent shareholders, no debt adjustment."""

from .assumptions import Scenario
from .dcf import DiscountedValue, discounted_value


def ddm_value(s: Scenario) -> DiscountedValue:
    if any(flow < 0 for flow in s.cash_flows):
        raise ValueError("dividends cannot be negative")
    return discounted_value(s)
