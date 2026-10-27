"""Readers for stored personal records, shared by HTTP routes, jobs and services.

Lives below the API layer so jobs and services never import from api.routes.
"""

from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, model_validator

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


RISK_GROUPS = ("very_safe", "cautious", "moderately_cautious", "balanced", "growth", "strong_growth")
RISK_OVERRIDE = ("settings", "risk_override")


class RiskOverride(ContractModel):
    """Group chosen by hand on Hồ sơ & rủi ro; replaces the survey group everywhere until cleared. None = use the survey."""
    group: Literal["very_safe", "cautious", "moderately_cautious", "balanced", "growth", "strong_growth"] | None = None


def risk_override(repo, owner) -> tuple[RiskOverride, int]:
    record = read_version(repo, owner, *RISK_OVERRIDE, None)
    return (RiskOverride.model_validate(record.payload), record.version) if record else (RiskOverride(), 0)


def effective_risk(repo, owner, assessment: RiskAssessment | None) -> RiskAssessment | None:
    """The survey assessment with the owner's manual group applied (score and answers stay the survey's)."""
    if assessment is None:
        return None
    chosen, _ = risk_override(repo, owner)
    return assessment.model_copy(update={"group": chosen.group}) if chosen.group else assessment


class TradingSettings(ContractModel):
    fee_rate: Ratio  # owner's broker fee as a fraction of order value, from their fee schedule


def trading_settings(repo, owner) -> TradingSettings | None:
    record = read_version(repo, owner, "settings", "trading", None)
    return TradingSettings.model_validate(record.payload) if record else None


class ValuationSettings(ContractModel):
    required_return: Ratio = Decimal("0.13")
    long_term_growth: Ratio = Decimal("0.05")
    threshold: Ratio = Decimal("0.2")

    @model_validator(mode="after")
    def _sensible(self):
        if self.required_return <= self.long_term_growth:
            raise ValueError("required return must exceed long-term growth")
        if not Decimal("0") < self.threshold < Decimal("1"):
            raise ValueError("threshold must be between 0 and 1")
        return self


class PortfolioSettings(ContractModel):
    """Owner's display threshold for concentration (one ticker or one sector, on investable capital); not an allocation rule."""
    concentration_limit: Ratio = Decimal("0.25")
    journal_review_threshold: Ratio = Decimal("0.15")  # Nhật ký: remind again each time the price moves this much from the recorded price
    drawdown_threshold: Ratio = Decimal("0.30")  # Kế hoạch sụt giảm: remind once when a held ticker is this far below its average cost

    @model_validator(mode="after")
    def _sensible(self):
        if not Decimal("0") < self.concentration_limit <= Decimal("1"):
            raise ValueError("concentration limit must be above 0 and at most 100%")
        if not Decimal("0.01") <= self.journal_review_threshold <= Decimal("1"):
            raise ValueError("journal review threshold must be between 1% and 100%")
        if not Decimal("0.01") <= self.drawdown_threshold <= Decimal("0.95"):
            raise ValueError("drawdown threshold must be between 1% and 95%")
        return self


def portfolio_settings(repo, owner) -> tuple[PortfolioSettings, int]:
    record = read_version(repo, owner, "settings", "portfolio", None)
    return (PortfolioSettings.model_validate(record.payload), record.version) if record else (PortfolioSettings(), 0)


def valuation_settings(repo, owner) -> tuple[ValuationSettings, int]:
    record = read_version(repo, owner, "settings", "valuation", None)
    return (ValuationSettings.model_validate(record.payload), record.version) if record else (ValuationSettings(), 0)


NOTIFICATIONS = ("settings", "notifications")
NOTIFICATIONS_DISABLED = NotificationSettings(enabled=False, members_may_view_personal_data=False, scheduled_enabled=False)


def notification_settings(repo, owner) -> tuple[NotificationSettings, int]:
    record = read_version(repo, owner, *NOTIFICATIONS, None)
    return (NotificationSettings.model_validate(record.payload), record.version) if record else (NOTIFICATIONS_DISABLED, 0)
