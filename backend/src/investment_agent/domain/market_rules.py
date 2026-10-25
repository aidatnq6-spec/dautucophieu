"""HOSE trading rules (lot, tick, price band, sell tax) from a pinned, sourced config.

Each figure in config/market-rules-hose.json records its legal basis and how it
was verified; see docs/decisions/market-rules.md. Callers that rely on a figure
still marked secondary should keep asking the owner to confirm.
"""

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path

from .pinned import CONFIG_DIR, load_pinned

RULES_PATH = CONFIG_DIR / "market-rules-hose.json"
PINNED_DIGESTS = {
    "hose-rules-2026-10-25.1": "421fe325e975d299742a85a0b0673d21a48483e76b91ead0efe65e1cd3ac46cd",
}


class MarketRules:
    def __init__(self, data: dict, digest: str):
        self.version, self.digest = data["version"], digest
        self.round_lot = int(data["round_lot"])
        self.max_round_lot_order = int(data["max_round_lot_order"])
        self._ticks = [(None if t["below"] is None else Decimal(t["below"]), Decimal(t["tick"])) for t in data["tick_sizes"]]
        self.daily_price_band = Decimal(data["daily_price_band"])
        self.settlement_cycle_days = int(data["settlement_cycle_days"])
        self.sell_tax_rate = Decimal(data["sell_tax_rate"])
        self.dividend_tax_rate = Decimal(data["dividend_tax_rate"])
        self.statuses = {k: v["status"] for k, v in data["sources"].items()}

    def tick_size(self, price: Decimal) -> Decimal:
        return next(tick for below, tick in self._ticks if below is None or price < below)

    def is_valid_price(self, price: Decimal) -> bool:
        return price > 0 and price % self.tick_size(price) == 0

    def price_limits(self, reference: Decimal) -> tuple[Decimal, Decimal]:
        """(ceiling, floor): ceiling rounded down, floor rounded up to the tick of each price."""
        raw_ceiling, raw_floor = reference * (1 + self.daily_price_band), reference * (1 - self.daily_price_band)
        tick_c, tick_f = self.tick_size(raw_ceiling), self.tick_size(raw_floor)
        ceiling = (raw_ceiling / tick_c).to_integral_value(rounding=ROUND_FLOOR) * tick_c
        floor = (raw_floor / tick_f).to_integral_value(rounding=ROUND_CEILING) * tick_f
        return ceiling, floor

    def round_lot_shares(self, amount: Decimal, price: Decimal, *, fee_rate: Decimal) -> int:
        """Largest round-lot quantity whose cost plus fee fits the amount, capped at the per-order maximum."""
        affordable = int((amount / (price * (1 + fee_rate))).to_integral_value(rounding=ROUND_FLOOR))
        return min(affordable // self.round_lot * self.round_lot, self.max_round_lot_order)

    def sell_tax(self, price: Decimal, quantity: int) -> Decimal:
        return price * quantity * self.sell_tax_rate


def load_market_rules(path: Path = RULES_PATH) -> MarketRules:
    data, digest = load_pinned(path, PINNED_DIGESTS)
    return MarketRules(data, digest)
