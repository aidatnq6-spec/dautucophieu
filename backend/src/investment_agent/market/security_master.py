"""Ticker → issuer mapping over time. Entity IDs are stable; tickers and exchanges are not."""

from collections import defaultdict
from datetime import date

from pydantic import model_validator

from investment_agent.domain.models import ContractModel, NonemptyId


class MasterError(ValueError):
    pass


class TickerMapping(ContractModel):
    entity_id: NonemptyId
    ticker: NonemptyId
    exchange: NonemptyId
    valid_from: date
    valid_to: date | None  # inclusive; None = current

    @model_validator(mode="after")
    def _ordered(self):
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to before valid_from")
        return self

    def covers(self, day: date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day <= self.valid_to)


class SecurityMaster:
    def __init__(self, mappings: list[TickerMapping]):
        by_ticker = defaultdict(list)
        for m in mappings:
            by_ticker[m.ticker].append(m)
        for items in by_ticker.values():
            items.sort(key=lambda m: m.valid_from)
            for a, b in zip(items, items[1:]):
                if a.valid_to is None or b.valid_from <= a.valid_to:
                    raise MasterError("overlapping mappings for one ticker")
        self._mappings = list(mappings)

    def resolve(self, ticker: str, day: date) -> str:
        found = [m.entity_id for m in self._mappings if m.ticker == ticker and m.covers(day)]
        if len(found) != 1:
            raise MasterError("ticker not mapped on that date")
        return found[0]

    def exchange_on(self, entity_id: str, day: date) -> str:
        found = [m.exchange for m in self._mappings if m.entity_id == entity_id and m.covers(day)]
        if len(found) != 1:
            raise MasterError("entity has no single listing on that date")
        return found[0]
