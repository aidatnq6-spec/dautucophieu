"""Local USD spend ledger: reserve an estimate before a call, reconcile after.

Reserved and uncertain entries count at their reserved amount until settled
with the actual cost; settling twice changes nothing. This is a local guard,
not a guarantee against the provider's invoice.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from uuid import uuid4


class BudgetError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SpendSummary:
    reserved_usd: Decimal
    uncertain_usd: Decimal
    settled_usd: Decimal


class SpendLedger:
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False, timeout=10)
        self._lock = Lock()
        self._db.execute("CREATE TABLE IF NOT EXISTS ai_spend (id TEXT PRIMARY KEY, job_id TEXT, month TEXT, status TEXT, reserved TEXT, actual TEXT)")
        self._db.commit()

    def _rows(self, where: str, args: tuple):
        return self._db.execute(f"SELECT status, reserved, actual FROM ai_spend WHERE {where}", args).fetchall()

    @staticmethod
    def _counted(rows) -> Decimal:
        return sum((Decimal(actual) if status == "settled" else Decimal(reserved) for status, reserved, actual in rows if status != "released"),
                   Decimal(0))

    def reserve(self, job_id: str, estimate: Decimal, *, monthly: Decimal, per_request: Decimal, per_job: Decimal, now: datetime,
                max_concurrency: int | None = None) -> str:
        month = now.strftime("%Y-%m")
        with self._lock, self._db:
            if estimate > per_request:
                raise BudgetError("per_request_cap")
            if self._counted(self._rows("month = ?", (month,))) + estimate > monthly:
                raise BudgetError("monthly_cap")
            if self._counted(self._rows("job_id = ?", (job_id,))) + estimate > per_job:
                raise BudgetError("per_job_cap")
            if max_concurrency is not None and len(self._rows("status = 'reserved'", ())) >= max_concurrency:
                raise BudgetError("concurrency_cap")
            rid = uuid4().hex
            self._db.execute("INSERT INTO ai_spend VALUES (?,?,?,?,?,?)", (rid, job_id, month, "reserved", format(estimate, "f"), None))
            return rid

    def _set(self, rid: str, status: str, actual: Decimal | None = None):
        with self._lock, self._db:
            row = self._db.execute("SELECT status FROM ai_spend WHERE id = ?", (rid,)).fetchone()
            if row is None or row[0] in {"settled", "released"}:
                return  # idempotent
            self._db.execute("UPDATE ai_spend SET status = ?, actual = ? WHERE id = ?", (status, None if actual is None else format(actual, "f"), rid))

    def settle(self, rid: str, actual: Decimal):
        self._set(rid, "settled", actual)

    def mark_uncertain(self, rid: str):
        self._set(rid, "uncertain")

    def release(self, rid: str):
        """Only when the request certainly did not reach the provider or was rejected without charge."""
        self._set(rid, "released")

    def summary(self, now: datetime) -> SpendSummary:
        rows = self._rows("month = ?", (now.strftime("%Y-%m"),))
        total = lambda wanted: sum((Decimal(actual if s == "settled" else r) for s, r, actual in rows if s == wanted), Decimal(0))
        return SpendSummary(reserved_usd=total("reserved"), uncertain_usd=total("uncertain"), settled_usd=total("settled"))
