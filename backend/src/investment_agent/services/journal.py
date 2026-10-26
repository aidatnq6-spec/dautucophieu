"""Investment journal stored in the owner's personal repository (`journal/main`), with the market context captured on save.

Personal data: stays on the owner's machine and in their Firestore; nothing here is ever sent to a model.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from investment_agent.domain.journal import EMOTION_VI, JournalEntry, add_note, due_reviews, mark_reviewed
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.series import SeriesStore
from investment_agent.market.trend import SnapshotStore
from investment_agent.notifications.render import _num, vnd
from investment_agent.services.holdings_view import fair_value_board
from investment_agent.services.records import read_version
from investment_agent.valuation.reference import metrics, year_end_prices

COLLECTION, RECORD = "journal", "main"


class EntryNotFound(LookupError):
    pass


def read_journal(repo, owner) -> tuple[list[JournalEntry], int]:
    """Entries oldest first and the record version; raises RepositoryUnavailable."""
    record = read_version(repo, owner, COLLECTION, RECORD, None)
    if record is None:
        return [], 0
    return [JournalEntry.model_validate(e) for e in record.payload.get("entries", [])], record.version


def _write(repo, owner, entries, version, request_id):
    return repo.write(owner, COLLECTION, RECORD, {"entries": [e.model_dump(mode="json") for e in entries]}, expected_version=version,
                      request_id=request_id)


def append_entry(repo, owner, entry: JournalEntry, *, request_id: str) -> JournalEntry:
    """Append once; a retry with the same entry id returns the stored entry unchanged."""
    entries, version = read_journal(repo, owner)
    existing = next((e for e in entries if e.entry_id == entry.entry_id), None)
    if existing is not None:
        return existing
    _write(repo, owner, [*entries, entry], version, request_id)
    return entry


def append_note(repo, owner, entry_id: str, *, text: str, on: date, request_id: str) -> JournalEntry:
    entries, version = read_journal(repo, owner)
    if not any(e.entry_id == entry_id for e in entries):
        raise EntryNotFound(entry_id)
    updated = [add_note(e, text=text, on=on) if e.entry_id == entry_id else e for e in entries]
    _write(repo, owner, updated, version, request_id)
    return next(e for e in updated if e.entry_id == entry_id)


def replace_entries(repo, owner, entries: list[JournalEntry], version: int, *, request_id: str):
    """Used by the review job to record reminders already sent (reviewed levels only)."""
    return _write(repo, owner, entries, version, request_id)


def capture_context(symbol: str, *, market, data_dir: Path | None, repo, owner, today: date) -> dict:
    """Price, P/E, Định giá verdict, D1 MACD/RSI and VN-Index at this moment; anything unavailable is left as None."""
    point = market.price(symbol)
    context = {"price": str(point.price) if point is not None else None, "pe": None, "verdict": None, "macd_d1": None, "rsi_d1": None,
               "vnindex": None}
    if data_dir is None:
        return context
    data_dir = Path(data_dir)
    series = SeriesStore(data_dir / "trend-sources")
    if closes := series.read("VNINDEX-1d"):
        context["vnindex"] = str(Decimal(str(closes[-1][1])).normalize())
    snapshot = SnapshotStore(data_dir / "trend").latest() or {}
    for group in snapshot.get("groups", []):
        for row in group.get("rows", []):
            if row.get("id") == symbol:
                d1 = row.get("cells", {}).get("D1") or {}
                context.update(macd_d1=d1.get("macd"), rsi_d1=d1.get("rsi"))
    try:
        board = fair_value_board(data_dir, market, repo, owner, held=set(), today=today)
        row = next((r for r in board["rows"] if r["symbol"] == symbol), None)
        if row is not None and row["verdict"] in ("cheap", "fair", "expensive"):
            context["verdict"] = row["verdict"]
        record = FundamentalsStore(data_dir / "fundamentals").read(symbol)
        m = metrics(record, today=today, year_end_prices=year_end_prices(series.read(f"{symbol}-1d"), today=today)) if record else None
        if m and point is not None and m["eps_ttm"] and m["eps_ttm"] > 0:
            context["pe"] = str((point.price / m["eps_ttm"]).quantize(Decimal("0.1"), ROUND_HALF_UP))
    except Exception:  # valuation is a nice-to-have in the snapshot; never block saving the entry
        pass
    return context


def change(recorded: str | None, current: Decimal | None) -> str | None:
    if recorded in (None, "", "0") or current is None:
        return None
    return str((Decimal(str(current)) / Decimal(recorded) - 1).quantize(Decimal("0.0001"), ROUND_HALF_UP))


KIND_VI = {"buy": "Mua", "sell": "Bán", "hold": "Đang giữ"}


def render_review(due: list[dict]) -> str:
    """Plain-text Telegram reminder: what was written at the time, beside how far the price has moved. No advice."""
    lines = ["Nhật ký — xem lại quyết định (giá đã đi xa so với lúc ghi)"]
    for d in due:
        e = d["entry"]
        lines += ["", f"{e.symbol} · {KIND_VI[e.kind]} ngày {e.created_on:%d/%m/%Y}",
                  f"Giá lúc ghi {vnd(e.context.get('price'))} → nay {vnd(d['price'])} ({_num(Decimal(d['change']) * 100, 1, sign=True)}%)",
                  f"Lý do đã ghi: {e.reason or 'không ghi'}"]
        if e.emotion:
            lines.append(f"Cảm xúc lúc đó: {EMOTION_VI[e.emotion]}" + (f" — {e.emotion_note}" if e.emotion_note else ""))
    return "\n".join(lines)


def review_run(repo, owner, *, prices: dict[str, Decimal], threshold: Decimal, send, request_id: str) -> dict:
    """Send one message for every entry that moved another `threshold`; mark them reviewed only after a successful send."""
    entries, version = read_journal(repo, owner)
    due = due_reviews(entries, prices=prices, threshold=threshold)
    if not due:
        return {"due": 0, "sent": False}
    if not send(render_review(due)):
        return {"due": len(due), "sent": False}
    levels = {d["entry"].entry_id: d["level"] for d in due}
    replace_entries(repo, owner, [mark_reviewed(e, level=levels[e.entry_id]) if e.entry_id in levels else e for e in entries], version,
                    request_id=request_id)
    return {"due": len(due), "sent": True}
