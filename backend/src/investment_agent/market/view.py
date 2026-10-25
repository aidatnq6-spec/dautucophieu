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


class EmptyMarket:
    provenance = "none"

    def price(self, entity_id):
        return None

    def evidence(self, entity_id):
        return []

    def industry(self, entity_id):
        return None


@dataclass
class SyntheticMarket:
    prices: dict[str, PricePoint] = field(default_factory=dict)
    documents: dict[str, list[EvidenceRef]] = field(default_factory=dict)
    industries: dict[str, str] = field(default_factory=dict)
    provenance: str = "synthetic"

    def price(self, entity_id):
        return self.prices.get(entity_id)

    def evidence(self, entity_id):
        return list(self.documents.get(entity_id, []))

    def industry(self, entity_id):
        return self.industries.get(entity_id)
