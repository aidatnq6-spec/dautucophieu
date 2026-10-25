"""Readers for stored personal records, shared by HTTP routes, jobs and services.

Lives below the API layer so jobs and services never import from api.routes.
"""

from pydantic import AwareDatetime

from investment_agent.domain.ledger import parse_events
from investment_agent.domain.models import ContractModel, Ratio
from investment_agent.domain.reconciliation import Change, apply_amendments, parse_amendments
from investment_agent.domain.risk import RiskAssessment
from investment_agent.notifications.outbox import NotificationSettings
from investment_agent.repositories.personal_cache import PersonalView


def read_current(repo, owner, collection, record_id):
    """Return (record or None, stale). Raises RepositoryUnavailable."""
    result = repo.read(owner, collection, record_id)
    if isinstance(result, PersonalView):
        return result.record, result.stale
    return result, False


def read_version(repo, owner, collection, record_id, version):
    """Exact historical revision from the authoritative store, never the cache."""
    return getattr(repo, "authoritative", repo).read(owner, collection, record_id, version=version)


class LedgerBook:
    """Stored ledger payload: original events, ordered amendments and the change log."""

    def __init__(self, record):
        payload = record.payload if record else {}
        self.events = parse_events(payload.get("events", []))
        self.amendments = parse_amendments(payload.get("amendments", []))
        self.changes = [Change.model_validate(c) for c in payload.get("changes", [])]

    def effective(self):
        return apply_amendments(self.events, self.amendments)

    def payload(self):
        return {"schema_version": "2", "events": [e.model_dump(mode="json") for e in self.events],
                "amendments": [a.model_dump(mode="json") for a in self.amendments],
                "changes": [c.model_dump(mode="json") for c in self.changes]}


class StoredRisk(ContractModel):
    schema_version: str = "1"
    assessment: RiskAssessment
    assessed_at: AwareDatetime
    profile_version: int | None


class TradingSettings(ContractModel):
    fee_rate: Ratio  # owner's broker fee as a fraction of order value, from their fee schedule


def trading_settings(repo, owner) -> TradingSettings | None:
    record = read_version(repo, owner, "settings", "trading", None)
    return TradingSettings.model_validate(record.payload) if record else None


NOTIFICATIONS = ("settings", "notifications")
NOTIFICATIONS_DISABLED = NotificationSettings(enabled=False, members_may_view_personal_data=False, scheduled_enabled=False)


def notification_settings(repo, owner) -> tuple[NotificationSettings, int]:
    record = read_version(repo, owner, *NOTIFICATIONS, None)
    return (NotificationSettings.model_validate(record.payload), record.version) if record else (NOTIFICATIONS_DISABLED, 0)
