"""Read-only market inputs for overview and research pages.

The application ships EmptyMarket: no licensed source is connected, so every
price and evidence lookup is missing and recommendations stay insufficient.
SyntheticMarket exists for labelled fixtures and browser tests only.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PricePoint:
    price: Decimal
    session_date: date


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    title: str
    kind: str
    source_url: str
    published: str
    ticker: str | None = None


class MarketView(Protocol):
    provenance: str

    def price(self, entity_id: str) -> PricePoint | None: ...

    def evidence(self, entity_id: str) -> list[EvidenceRef]: ...

    def industry(self, entity_id: str) -> str | None: ...

    def recent_closes(self, entity_id: str, n: int) -> list[PricePoint]: ...


class EmptyMarket:
    provenance = "none"

    def price(self, entity_id):
        return None

    def evidence(self, entity_id):
        return []

    def industry(self, entity_id):
        return None

    def recent_closes(self, entity_id, n):
        return []


@dataclass
class SyntheticMarket:
    prices: dict[str, PricePoint] = field(default_factory=dict)
    documents: dict[str, list[EvidenceRef]] = field(default_factory=dict)
    industries: dict[str, str] = field(default_factory=dict)
    history: dict[str, list[PricePoint]] = field(default_factory=dict)  # oldest first
    provenance: str = "synthetic"

    def price(self, entity_id):
        return self.prices.get(entity_id)

    def recent_closes(self, entity_id, n):
        points = self.history.get(entity_id) or ([self.prices[entity_id]] if entity_id in self.prices else [])
        return list(points[-n:])

    def evidence(self, entity_id):
        return list(self.documents.get(entity_id, []))

    def industry(self, entity_id):
        return self.industries.get(entity_id)


class StoreMarket:
    """Latest stored close per entity from the local Parquet store (e.g. Vnstock restricted mode).

    Prices older than max_age_days count as missing. No evidence documents are
    provided, so recommendations stay insufficient while portfolio values work.
    """

    def __init__(self, store, cal, *, today, provenance: str = "vnstock_adjusted", max_age_days: int = 10, industries=None):
        self.store, self.cal, self.today, self.provenance = store, cal, today, provenance
        self.max_age_days, self.industries = max_age_days, industries or {}

    def price(self, entity_id):
        view = self.store.latest(entity_id)
        if not view:
            return None
        day = max(view)
        if (self.today() - day).days > self.max_age_days:
            return None
        return PricePoint(view[day][0].close, day)

    def recent_closes(self, entity_id, n):
        """Last n stored closes, oldest first, whatever their age."""
        view = self.store.latest(entity_id)
        return [PricePoint(view[d][0].close, d) for d in sorted(view)[-n:]]

    def evidence(self, entity_id):
        return []

    def industry(self, entity_id):
        return self.industries.get(entity_id)
