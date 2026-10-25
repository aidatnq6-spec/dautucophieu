"""Ledger corrections as recoverable amendments with an audit trail.

The stored ledger keeps every original event and an ordered amendment list.
Replacing or cancelling never deletes history: the effective ledger is derived
by applying amendments, then replayed from scratch, so a corrected ledger is
identical to one entered correctly the first time.
"""

from datetime import date
from typing import Literal

from pydantic import Field, TypeAdapter, model_validator

from .corporate_actions import EventId, LedgerError
from .ledger import LedgerEvent
from .models import ContractModel


class Amendment(ContractModel):
    amendment_id: EventId
    action: Literal["replace", "cancel", "restore"]
    target_event_id: EventId
    replacement: LedgerEvent | None = None
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _shape(self):
        if (self.action == "replace") != (self.replacement is not None):
            raise ValueError("only replace carries a replacement event")
        if self.replacement is not None and self.replacement.event_id != self.target_event_id:
            raise ValueError("replacement keeps the target event_id")
        return self


class AuditEntry(ContractModel):
    amendment_id: EventId
    action: Literal["replace", "cancel", "restore"]
    target_event_id: EventId
    before: dict | None
    after: dict | None
    affected_from: date


class Change(ContractModel):
    """One ledger mutation: snapshots built before ledger_version and dated on/after affected_from are stale."""

    ledger_version: int = Field(strict=True, ge=1)
    affected_from: date


class AmendedLedger(ContractModel):
    events: tuple[LedgerEvent, ...]
    audit: tuple[AuditEntry, ...]


_AMENDMENTS = TypeAdapter(list[Amendment])


def parse_amendments(raw: list[dict]) -> list[Amendment]:
    return _AMENDMENTS.validate_python(raw)


def apply_amendments(events: list, amendments: list[Amendment]) -> AmendedLedger:
    current = {e.event_id: e for e in events}
    order = [e.event_id for e in events]
    cancelled: set[str] = set()
    seen: set[str] = set()
    audit = []
    for a in amendments:
        if a.amendment_id in seen:
            raise LedgerError("duplicate_amendment", a.amendment_id)
        seen.add(a.amendment_id)
        target = current.get(a.target_event_id)
        if target is None:
            raise LedgerError("unknown_target", a.amendment_id)
        before = target.model_dump(mode="json")
        if a.action == "restore":
            if a.target_event_id not in cancelled:
                raise LedgerError("not_cancelled", a.amendment_id)
            cancelled.discard(a.target_event_id)
            audit.append(AuditEntry(amendment_id=a.amendment_id, action=a.action, target_event_id=a.target_event_id,
                                    before=None, after=before, affected_from=target.effective_at))
            continue
        if a.target_event_id in cancelled:
            raise LedgerError("already_cancelled", a.amendment_id)
        if a.action == "cancel":
            cancelled.add(a.target_event_id)
            audit.append(AuditEntry(amendment_id=a.amendment_id, action=a.action, target_event_id=a.target_event_id,
                                    before=before, after=None, affected_from=target.effective_at))
        else:
            current[a.target_event_id] = a.replacement
            audit.append(AuditEntry(amendment_id=a.amendment_id, action=a.action, target_event_id=a.target_event_id,
                                    before=before, after=a.replacement.model_dump(mode="json"),
                                    affected_from=min(target.effective_at, a.replacement.effective_at)))
    return AmendedLedger(events=tuple(current[i] for i in order if i not in cancelled), audit=tuple(audit))


def snapshot_invalidated(*, as_of: date, built_on_version: int, changes: list[Change]) -> bool:
    return any(c.ledger_version > built_on_version and c.affected_from <= as_of for c in changes)
