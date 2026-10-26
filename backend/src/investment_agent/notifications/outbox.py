"""Report outbox and per-part delivery records (local SQLite).

Delivery state is kept per (report, report version, destination, part). Parts
go out in order; a sent part is never resent; an unknown part stops delivery
until the owner checks the group and resolves it. Exactly-once is not claimed:
an unknown outcome may have been delivered.
"""

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Literal

from pydantic import Field, model_validator

from investment_agent.domain.models import ContractModel

from .render import render_report, split_message


class NotificationSettings(ContractModel):
    enabled: bool
    chat_id: str | None = Field(default=None, pattern=r"^-?\d{3,20}$")
    members_may_view_personal_data: bool
    scheduled_enabled: bool

    @model_validator(mode="after")
    def _confirmed(self):
        if self.enabled and (not self.chat_id or not self.members_may_view_personal_data):
            raise ValueError("enabling needs a group id and confirmation that its members may see personal portfolio data")
        if self.scheduled_enabled and not self.enabled:
            raise ValueError("scheduled sending requires sending to be enabled")
        return self


@dataclass(frozen=True)
class PartRecord:
    index: int
    count: int
    status: str
    message_id: int | None


@dataclass(frozen=True)
class DeliveryResult:
    status: Literal["disabled", "not_publishable", "sent", "retryable", "unknown", "failed"]
    parts_sent: int = 0
    parts_total: int = 0


class DeliveryStore:
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, timeout=10, check_same_thread=False)
        self._lock = Lock()
        with self._db:
            self._db.execute("""CREATE TABLE IF NOT EXISTS deliveries (report_id TEXT, version TEXT, destination TEXT, part INTEGER, parts INTEGER,
                                digest TEXT, status TEXT, message_id INTEGER, attempts INTEGER, PRIMARY KEY (report_id, version, destination, part))""")
            self._db.execute("CREATE TABLE IF NOT EXISTS outbox (report_id TEXT PRIMARY KEY, status TEXT)")

    def ensure(self, report_id, version, destination, texts):
        with self._lock, self._db:
            for i, text in enumerate(texts):
                self._db.execute("INSERT OR IGNORE INTO deliveries VALUES (?,?,?,?,?,?,?,?,?)",
                                 (report_id, version, destination, i, len(texts), hashlib.sha256(text.encode()).hexdigest(), "pending", None, 0))

    def _rows(self, report_id, version, destination):
        return self._db.execute("SELECT part, parts, status, message_id FROM deliveries WHERE report_id=? AND version=? AND destination=? ORDER BY part",
                                (report_id, version, destination)).fetchall()

    def parts(self, report_id, destination, version="1") -> list[PartRecord]:
        return [PartRecord(*row) for row in self._rows(report_id, version, destination)]

    def set(self, report_id, version, destination, part, status, message_id=None):
        with self._lock, self._db:
            self._db.execute("UPDATE deliveries SET status=?, message_id=COALESCE(?, message_id), attempts=attempts+1 "
                             "WHERE report_id=? AND version=? AND destination=? AND part=?", (status, message_id, report_id, version, destination, part))

    def resolve_unknown(self, report_id, destination, part, *, outcome: Literal["received", "not_received"], version="1"):
        """Owner checked the group: a received part becomes sent, otherwise it may be retried."""
        with self._lock, self._db:
            self._db.execute("UPDATE deliveries SET status=? WHERE report_id=? AND version=? AND destination=? AND part=? AND status IN ('unknown', 'sending')",
                             ("sent" if outcome == "received" else "retryable", report_id, version, destination, part))

    # Outbox used by the report pipeline: queued only after a report is persisted.
    def enqueue(self, report_id):
        with self._lock, self._db:
            self._db.execute("INSERT OR IGNORE INTO outbox VALUES (?, 'queued')", (report_id,))

    def queued(self) -> list[str]:
        return [r[0] for r in self._db.execute("SELECT report_id FROM outbox WHERE status='queued' ORDER BY rowid").fetchall()]

    def mark_processed(self, report_id):
        with self._lock, self._db:
            self._db.execute("UPDATE outbox SET status='processed' WHERE report_id=?", (report_id,))


def deliver(report: dict, settings: NotificationSettings, sender, store: DeliveryStore, market: dict | None = None) -> DeliveryResult:
    if not settings.enabled:
        return DeliveryResult("disabled")
    if report["status"] != "published":
        return DeliveryResult("not_publishable")
    texts = split_message(render_report(report, market))
    rid, version, dest = report["report_id"], report.get("report_version", "1"), settings.chat_id
    store.ensure(rid, version, dest, texts)
    rows = store.parts(rid, dest, version)
    if any(r.status in {"unknown", "sending"} for r in rows):  # "sending" left by a crash: outcome unknown
        return DeliveryResult("unknown", sum(r.status == "sent" for r in rows), len(rows))
    sent = sum(r.status == "sent" for r in rows)
    for row, text in zip(rows, texts):
        if row.status == "sent":
            continue
        if row.status == "failed":
            return DeliveryResult("failed", sent, len(rows))
        store.set(rid, version, dest, row.index, "sending")
        outcome = sender.send(dest, text)
        store.set(rid, version, dest, row.index, outcome.status, outcome.message_id)
        if outcome.status != "sent":
            return DeliveryResult(outcome.status, sent, len(rows))
        sent += 1
    return DeliveryResult("sent", sent, len(rows))
