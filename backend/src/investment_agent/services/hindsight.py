"""Hậu kiểm quyết định from the owner's stored records and closes; personal data, never sent to a model."""

from datetime import date
from pathlib import Path

from investment_agent.domain.hindsight import hindsight
from investment_agent.market.series import SeriesStore
from investment_agent.services.journal import read_journal
from investment_agent.services.records import LedgerBook, portfolio_settings, read_version
from investment_agent.services.theses import read_theses


def hindsight_for(repo, owner, data_dir: Path, *, today: date) -> dict:
    """Raises RepositoryUnavailable."""
    events = list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)
    store = SeriesStore(Path(data_dir) / "trend-sources")
    symbols = {e.security_id for e in events if getattr(e, "security_id", None)} | {p.security_id for e in events for p in getattr(e, "positions", ())}
    closes = {s: [(t.date(), v) for t, v in store.read(f"{s}-1d")] for s in symbols}
    journal = [{"ledger_event_id": e.ledger_event_id, "emotion": e.emotion} for e in read_journal(repo, owner)[0]]
    threshold = portfolio_settings(repo, owner)[0].drawdown_threshold
    out = hindsight(events, closes=closes, index=[(t.date(), v) for t, v in store.read("VNINDEX-1d")], journal=journal,
                    theses=read_theses(repo, owner)[0], threshold=threshold, today=today)
    return {**out, "threshold": str(threshold), "as_of": today.isoformat()}
