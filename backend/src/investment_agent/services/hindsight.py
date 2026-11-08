"""Hậu kiểm quyết định from the owner's stored records and closes; personal data, never sent to a model."""

from datetime import date
from pathlib import Path

from investment_agent.domain.hindsight import hindsight, imported_hindsight
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
    entries = read_journal(repo, owner)[0]
    journal = [{"ledger_event_id": e.ledger_event_id, "emotion": e.emotion} for e in entries]
    old = [{"entry_id": e.entry_id, "symbol": e.symbol, "kind": e.kind, "date": e.created_on, "price": e.imported.get("price"), "qty": e.imported.get("qty"), "pnl": e.imported.get("pnl")}
           for e in entries if e.imported and e.imported.get("asset") == "Cổ phiếu" and e.kind in ("buy", "sell")]
    threshold = portfolio_settings(repo, owner)[0].drawdown_threshold
    index = [(t.date(), v) for t, v in store.read("VNINDEX-1d")]
    imported = imported_hindsight(old, closes={s: [(t.date(), v) for t, v in store.read(f"{s}-1d")] for s in {r["symbol"] for r in old}}, index=index, today=today) if old else None
    out = hindsight(events, closes=closes, index=index, journal=journal,
                    theses=read_theses(repo, owner)[0], threshold=threshold, today=today)
    return {**out, "imported": imported, "threshold": str(threshold), "as_of": today.isoformat()}
