"""Raw daily bars stored as immutable per-entity revisions in Parquet.

Bulk path: one Parquet file per (entity, revision), written to a temp file and
atomically replaced, then listed in the entity's manifest. A file not in the
manifest is an orphan and never read. Corrections arrive as new revisions; the
latest view takes each session from the newest revision that has it, and any
earlier revision can still be read. Missing or suspended sessions stay empty —
nothing is forward-filled — and adjustment factors never modify raw prices.
"""

import json
import re
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import AwareDatetime, Field, model_validator

from investment_agent.domain.models import ContractModel, NonemptyId, UnsignedAmount
from investment_agent.domain.pinned import content_digest

from .calendar import TradingCalendar

_ID = r"^[A-Za-z0-9_.-]{1,128}$"
_DECIMALS = ("open", "high", "low", "close")


class PriceError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


class PriceBar(ContractModel):
    entity_id: str = Field(pattern=_ID)
    session_date: date
    open: UnsignedAmount
    high: UnsignedAmount
    low: UnsignedAmount
    close: UnsignedAmount
    volume: int = Field(strict=True, ge=0)
    currency: str
    source_id: NonemptyId
    observed_at: AwareDatetime
    provenance_mode: Literal["synthetic", "historical_as_reported", "latest_restated"]


class SessionRow(ContractModel):
    session_date: date
    status: Literal["traded", "suspended", "missing"]
    open: UnsignedAmount | None = None
    high: UnsignedAmount | None = None
    low: UnsignedAmount | None = None
    close: UnsignedAmount | None = None
    volume: int | None = None
    revision_id: str | None = None


class AdjustmentFactor(ContractModel):
    """Multiplier for prices before ex_date (e.g. 0.5 for a 1→2 split)."""

    entity_id: NonemptyId
    action_id: NonemptyId
    ex_date: date
    factor: UnsignedAmount
    kind: Literal["split", "cash_dividend", "stock_dividend"]
    source_id: NonemptyId

    @model_validator(mode="after")
    def _positive(self):
        if self.factor <= 0:
            raise ValueError("factor must be positive")
        return self


class AdjustedRow(ContractModel):
    session_date: date
    close: UnsignedAmount | None
    adjusted_close: UnsignedAmount | None


def _check(cal: TradingCalendar, b: PriceBar):
    if b.currency != "VND":
        raise PriceError("currency", b.entity_id)
    if min(b.open, b.high, b.low, b.close) <= 0:
        raise PriceError("non_positive_price", b.entity_id)
    if b.high < max(b.open, b.close, b.low) or b.low > min(b.open, b.close):
        raise PriceError("ohlc_inconsistent", f"{b.entity_id} {b.session_date}")
    try:
        on_session = cal.is_session(b.session_date)
    except ValueError:
        on_session = False
    if not on_session:
        raise PriceError("non_session_bar", f"{b.entity_id} {b.session_date}")


class PriceStore:
    """Single writer per data root."""

    def __init__(self, root: Path):
        self.root = Path(root) / "prices"

    def _dir(self, entity_id: str) -> Path:
        return self.root / entity_id

    def _manifest(self, entity_id: str) -> list[dict]:
        path = self._dir(entity_id) / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))["revisions"] if path.exists() else []

    def revisions(self, entity_id: str) -> tuple[str, ...]:
        return tuple(r["revision_id"] for r in self._manifest(entity_id))

    @staticmethod
    def _replace(data: bytes | None, table: pa.Table | None, target: Path):
        tmp = target.with_suffix(target.suffix + ".tmp")
        try:
            if table is not None:
                pq.write_table(table, tmp)
            else:
                tmp.write_bytes(data)
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)

    def write_revision(self, entity_id: str, revision_id: str, bars: list[PriceBar]) -> dict:
        rows = sorted((b.model_dump(mode="json") for b in bars), key=lambda r: r["session_date"])
        digest = content_digest(rows)
        manifest = self._manifest(entity_id)
        for entry in manifest:
            if entry["revision_id"] == revision_id:
                if entry["digest"] != digest:
                    raise PriceError("revision_conflict", f"{entity_id} {revision_id}")
                return entry  # retry of a published revision
        folder = self._dir(entity_id)
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{revision_id}.parquet"
        self._replace(None, pa.Table.from_pylist(rows), folder / name)
        entry = {"revision_id": revision_id, "file": name, "digest": digest, "rows": len(rows),
                 "first": rows[0]["session_date"], "last": rows[-1]["session_date"]}
        payload = json.dumps({"revisions": [*manifest, entry]}, ensure_ascii=False, indent=1).encode()
        self._replace(payload, None, folder / "manifest.json")
        return entry

    def read_revision(self, entity_id: str, entry: dict) -> list[PriceBar]:
        path = self._dir(entity_id) / entry["file"]
        rows = pq.read_table(path).to_pylist()
        if content_digest(rows) != entry["digest"]:
            raise PriceError("checksum_mismatch", f"{entity_id} {entry['revision_id']}")
        return [PriceBar.model_validate(r) for r in rows]

    def latest(self, entity_id: str, *, revision: str | None = None) -> dict[date, tuple[PriceBar, str]]:
        view = {}
        for entry in self._manifest(entity_id):
            for b in self.read_revision(entity_id, entry):
                view[b.session_date] = (b, entry["revision_id"])
            if entry["revision_id"] == revision:
                break
        return view


def ingest(store: PriceStore, cal: TradingCalendar, bars: list[PriceBar], *, revision_id: str) -> dict[str, dict]:
    """Validate every bar, then publish one revision per entity. Idempotent per revision_id."""
    if not re.fullmatch(_ID, revision_id):
        raise PriceError("invalid_revision_id")
    grouped: dict[str, list[PriceBar]] = {}
    for b in bars:
        _check(cal, b)
        grouped.setdefault(b.entity_id, []).append(b)
    for entity, items in grouped.items():
        if len({b.session_date for b in items}) != len(items):
            raise PriceError("duplicate_session", entity)
    return {entity: store.write_revision(entity, revision_id, items) for entity, items in sorted(grouped.items())}


def session_series(store: PriceStore, cal: TradingCalendar, entity_id: str, start: date, end: date, *,
                   suspended: set[date] = frozenset(), revision: str | None = None) -> list[SessionRow]:
    view = store.latest(entity_id, revision=revision)
    rows = []
    for day in cal.sessions(start, end):
        if day in view:
            b, rev = view[day]
            rows.append(SessionRow(session_date=day, status="traded", open=format(b.open, "f"), high=format(b.high, "f"),
                                   low=format(b.low, "f"), close=format(b.close, "f"), volume=b.volume, revision_id=rev))
        else:
            rows.append(SessionRow(session_date=day, status="suspended" if day in suspended else "missing"))
    return rows


def adjusted_closes(rows: list[SessionRow], factors: list[AdjustmentFactor]) -> list[AdjustedRow]:
    out = []
    for r in rows:
        if r.close is None:
            out.append(AdjustedRow(session_date=r.session_date, close=None, adjusted_close=None))
            continue
        multiplier = Decimal(1)
        for f in factors:
            if f.ex_date > r.session_date:
                multiplier *= f.factor
        out.append(AdjustedRow(session_date=r.session_date, close=format(r.close, "f"), adjusted_close=format(r.close * multiplier, "f")))
    return out


def load_history(store: PriceStore, cal: TradingCalendar, fetch: Callable[[str, date, date], list[PriceBar]], entity_id: str,
                 start: date, end: date, *, batch_sessions: int, checkpoint: Path, sleep: Callable[[float], None],
                 min_interval: float, revision_prefix: str) -> int:
    """Batched backfill resuming after the last completed batch. Returns batches fetched."""
    done = json.loads(checkpoint.read_text(encoding="utf-8")) if checkpoint.exists() else {}
    last = done.get(entity_id)
    sessions = [d for d in cal.sessions(start, end) if last is None or d > date.fromisoformat(last)]
    fetched = 0
    for i in range(0, len(sessions), batch_sessions):
        chunk = sessions[i:i + batch_sessions]
        if fetched:
            sleep(min_interval)
        ingest(store, cal, fetch(entity_id, chunk[0], chunk[-1]), revision_id=f"{revision_prefix}-{chunk[0]}-{chunk[-1]}")
        fetched += 1
        done[entity_id] = chunk[-1].isoformat()
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        PriceStore._replace(json.dumps(done).encode(), None, checkpoint)
    return fetched
