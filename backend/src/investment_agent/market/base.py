"""Provider interface. Capability claims require explicit evidence from an audit."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

from investment_agent.domain.models import Observation


class CapabilityState(str, Enum):
    VERIFIED = "verified"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderCapabilities:
    prices: CapabilityState = CapabilityState.UNKNOWN
    financials: CapabilityState = CapabilityState.UNKNOWN
    ratios: CapabilityState = CapabilityState.UNKNOWN
    actions: CapabilityState = CapabilityState.UNKNOWN
    disclosures: CapabilityState = CapabilityState.UNKNOWN
    publication_timestamps: CapabilityState = CapabilityState.UNKNOWN
    usage_rights: CapabilityState = CapabilityState.UNKNOWN


class MarketProvider(Protocol):
    def capabilities(self) -> ProviderCapabilities: ...

    def fetch_prices(self, entity_id: str) -> Sequence[Observation]: ...

    def fetch_financials(self, entity_id: str) -> Sequence[Observation]: ...

    def fetch_actions(self, entity_id: str) -> Sequence[Observation]: ...

    def fetch_disclosures(self, entity_id: str) -> Sequence[Observation]: ...
