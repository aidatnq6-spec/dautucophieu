"""Macro series kept by vintage: a revised release adds a vintage, never replaces one.

No GSO/SBV adapter ships yet: their access terms and formats are unverified
(Task 5), so observations enter only from audited sources or labelled fixtures.
"""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, Field

from investment_agent.domain.models import ContractModel, NonemptyId, SignedAmount

from .disclosures import EvidenceError

class MacroObservation(ContractModel):
    series_id: NonemptyId
    period: NonemptyId
    value: SignedAmount
    unit: Literal["percent", "VND", "index", "billion_VND", "USD_million"]
    source_id: NonemptyId
    source_url: str = Field(pattern=r"^https://\S+$")
    released_at: AwareDatetime
    vintage_id: NonemptyId
    provenance_mode: Literal["synthetic", "historical_as_reported", "latest_restated"]


class MacroVintages:
    def __init__(self):
        self._items: list[MacroObservation] = []

    def add(self, obs: MacroObservation):
        for existing in self._items:
            if (existing.series_id, existing.period, existing.vintage_id) == (obs.series_id, obs.period, obs.vintage_id):
                if existing != obs:
                    raise EvidenceError("vintage_conflict")
                return
        self._items.append(obs)

    def history(self, series_id: str, period: str) -> list[MacroObservation]:
        return sorted((o for o in self._items if (o.series_id, o.period) == (series_id, period)), key=lambda o: o.released_at)

    def latest(self, series_id: str, period: str) -> MacroObservation | None:
        rows = self.history(series_id, period)
        return rows[-1] if rows else None

    def as_of(self, series_id: str, period: str, when: datetime) -> MacroObservation | None:
        rows = [o for o in self.history(series_id, period) if o.released_at <= when]
        return rows[-1] if rows else None
