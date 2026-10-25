"""Local job leases and stage checkpoints in SQLite (one row per run key).

A lease is taken in an IMMEDIATE transaction, so two processes cannot both
hold a live lease for the same run key; an expired lease can be taken over.
This is the cross-process writer guard required by the Task 3 ruling.
"""

import json
import sqlite3
from pathlib import Path
from threading import Lock
from uuid import uuid4


class LeaseBusy(Exception):
    pass


class JobStore:
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, timeout=10, isolation_level=None, check_same_thread=False)
        self._lock = Lock()
        self._db.execute("""CREATE TABLE IF NOT EXISTS job_runs (run_key TEXT PRIMARY KEY, job_id TEXT UNIQUE, status TEXT, stages TEXT,
                            lease_owner TEXT, lease_until REAL, report_id TEXT, reason TEXT)""")
        self._db.execute("CREATE TABLE IF NOT EXISTS session_attempts (session TEXT PRIMARY KEY, count INTEGER)")

    def acquire(self, run_key: str, *, worker_id: str, now: float, ttl: float) -> str:
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                row = self._db.execute("SELECT job_id, status, lease_owner, lease_until FROM job_runs WHERE run_key = ?", (run_key,)).fetchone()
                if row and row[1] == "running" and row[2] != worker_id and row[3] > now:
                    raise LeaseBusy(run_key)
                job_id = row[0] if row else uuid4().hex
                if row:
                    self._db.execute("UPDATE job_runs SET status='running', lease_owner=?, lease_until=?, stages='[]', reason=NULL WHERE run_key=?",
                                     (worker_id, now + ttl, run_key))
                else:
                    self._db.execute("INSERT INTO job_runs VALUES (?,?,?,?,?,?,?,?)", (run_key, job_id, "running", "[]", worker_id, now + ttl, None, None))
                self._db.execute("COMMIT")
                return job_id
            except BaseException:
                self._db.execute("ROLLBACK")
                raise

    def stage(self, job_id: str, name: str):
        with self._lock:
            stages = json.loads(self._db.execute("SELECT stages FROM job_runs WHERE job_id = ?", (job_id,)).fetchone()[0])
            self._db.execute("UPDATE job_runs SET stages = ? WHERE job_id = ?", (json.dumps([*stages, name]), job_id))

    def finish(self, job_id: str, status: str, *, report_id: str | None = None, reason: str | None = None):
        with self._lock:
            self._db.execute("UPDATE job_runs SET status=?, report_id=?, reason=?, lease_until=0 WHERE job_id=?", (status, report_id, reason, job_id))

    def get(self, job_id: str) -> dict | None:
        row = self._db.execute("SELECT run_key, job_id, status, stages, report_id, reason FROM job_runs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return {"run_key": row[0], "job_id": row[1], "status": row[2], "stages": json.loads(row[3]), "report_id": row[4], "reason": row[5]}

    def count_attempt(self, session: str) -> int:
        with self._lock:
            self._db.execute("INSERT INTO session_attempts VALUES (?, 1) ON CONFLICT(session) DO UPDATE SET count = count + 1", (session,))
            return self._db.execute("SELECT count FROM session_attempts WHERE session = ?", (session,)).fetchone()[0]

    def attempts(self) -> dict[str, int]:
        return dict(self._db.execute("SELECT session, count FROM session_attempts").fetchall())

    def by_key(self, run_key: str) -> dict | None:
        row = self._db.execute("SELECT job_id FROM job_runs WHERE run_key = ?", (run_key,)).fetchone()
        return self.get(row[0]) if row else None
