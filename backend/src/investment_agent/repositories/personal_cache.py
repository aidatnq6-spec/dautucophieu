"""Disposable SQLite copies. Remote commits always precede cache writes."""

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from threading import Lock

from .personal import PersonalRecord, PersonalRepository, RepositoryUnavailable, canonical


class CacheUnavailable(Exception):
    pass


@dataclass(frozen=True)
class PersonalView:
    record: PersonalRecord | None
    stale: bool
    verified_at: datetime


class PersonalCache:
    """Separate disposable DB; never alters market catalog schema/user_version."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, timeout=10, check_same_thread=False)
        self._lock = Lock()
        self._db.execute("CREATE TABLE IF NOT EXISTS personal_cache (owner TEXT, collection TEXT, record_id TEXT, version INTEGER, data TEXT, verified_at TEXT, PRIMARY KEY(owner, collection, record_id))")
        self._db.commit()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._db.close()

    def save(self, record: PersonalRecord, verified_at: datetime):
        if verified_at.tzinfo is None:
            raise ValueError("Verification timestamp requires timezone")
        try:
            with self._lock, self._db:
                self._db.execute("""INSERT INTO personal_cache VALUES (?,?,?,?,?,?)
                    ON CONFLICT(owner,collection,record_id) DO UPDATE SET version=excluded.version,data=excluded.data,verified_at=excluded.verified_at
                    WHERE excluded.version >= personal_cache.version""", (record.owner_uid, record.collection, record.record_id, record.version, canonical(asdict(record)), verified_at.isoformat()))
        except sqlite3.Error:
            raise CacheUnavailable("Personal cache unavailable") from None

    def load(self, owner, collection, record_id):
        try:
            with self._lock:
                row = self._db.execute("SELECT data,verified_at FROM personal_cache WHERE owner=? AND collection=? AND record_id=?", (owner, collection, record_id)).fetchone()
            if row is None:
                return None
            return PersonalView(PersonalRecord(**json.loads(row[0])), True, datetime.fromisoformat(row[1]))
        except (sqlite3.Error, ValueError, TypeError):
            raise CacheUnavailable("Personal cache unavailable") from None

    def clear(self, owner, collection, record_id):
        try:
            with self._lock, self._db:
                self._db.execute("DELETE FROM personal_cache WHERE owner=? AND collection=? AND record_id=?", (owner, collection, record_id))
        except sqlite3.Error:
            raise CacheUnavailable("Personal cache unavailable") from None


class CachedPersonalRepository:
    def __init__(self, authoritative: PersonalRepository, cache: PersonalCache):
        self.authoritative, self.cache = authoritative, cache

    def read(self, context, collection, record_id):
        self.authoritative.authorize(context)
        self.authoritative.key(collection, record_id)
        try:
            record = self.authoritative.read(context, collection, record_id)
        except RepositoryUnavailable:
            try:
                view = self.cache.load(context.uid, collection, record_id)
            except CacheUnavailable:
                view = None
            if view is None:
                raise RepositoryUnavailable("No verified personal data available") from None
            return view
        verified_at = self.authoritative.clock()
        try:
            if record:
                self.cache.save(record, verified_at)
            else:
                self.cache.clear(context.uid, collection, record_id)
        except CacheUnavailable:
            pass  # Authoritative read succeeded; a disposable cache must not invalidate it.
        return PersonalView(record, False, verified_at)

    def write(self, context, collection, record_id, payload, *, expected_version, request_id):
        record = self.authoritative.write(context, collection, record_id, payload, expected_version=expected_version, request_id=request_id)
        try:
            self.cache.save(record, self.authoritative.clock())
        except CacheUnavailable:
            pass  # Retry with the same request ID can recover the remote committed result.
        return record

    def require_current(self, context, versions):
        # Always remote. A cached version never authorizes a new recommendation.
        return self.authoritative.require_current(context, versions)
