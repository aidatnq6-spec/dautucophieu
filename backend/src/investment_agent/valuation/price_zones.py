"""Price zone from the approved base-scenario value and the margin set in approved assumptions.

margin_of_safety = (base value − price) / base value; buy_below = base × (1 − required margin).
There is no default margin: without an approved one no zone exists.
"""

from decimal import Decimal
from typing import Literal

from investment_agent.domain.models import ContractModel, PlainDecimal


class Zone(ContractModel):
    basis: Literal["base_scenario_per_share"] = "base_scenario_per_share"
    fair_value: PlainDecimal
    buy_below: PlainDecimal
    down_value: PlainDecimal
    up_value: PlainDecimal
    margin_of_safety: PlainDecimal
    position: Literal["below_buy_zone", "between_buy_and_fair", "above_fair", "above_up_scenario"]


def compute_zone(*, base: Decimal, down: Decimal, up: Decimal, price: Decimal, required_margin: Decimal) -> Zone:
    if base <= 0:
        raise ValueError("base value must be positive")
    buy_below = base * (1 - required_margin)
    if price <= buy_below:
        position = "below_buy_zone"
    elif price <= base:
        position = "between_buy_and_fair"
    elif price <= up:
        position = "above_fair"
    else:
        position = "above_up_scenario"
    return Zone(fair_value=base, buy_below=buy_below, down_value=down, up_value=up, margin_of_safety=(base - price) / base, position=position)
