"""SQLite catalog and atomic publication of immutable local snapshots."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Callable, Iterable

from investment_agent.domain.models import Observation, SnapshotVersions
from investment_agent.market.parquet_store import ParquetStore


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    manifest_id: str
    versions: SnapshotVersions
    observation_ids: tuple[str, ...]
    observations: tuple[Observation, ...]


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class LocalRepository:
    """One writer per instance; SQLite serializes writers across processes."""

    def __init__(self, database: Path, store: ParquetStore):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.store = store
        self._lock = Lock()
        self._db = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA busy_timeout=30000")
        self._migrate()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self._db.close()

    def _migrate(self):
        with self._lock:
            version = self._db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                script = (Path(__file__).parent / "migrations" / "001_initial.sql").read_text(encoding="utf-8")
                self._db.executescript("BEGIN IMMEDIATE;\n" + script + "\nPRAGMA user_version=1;\nCOMMIT;")
            elif version != 1:
                raise ValueError(f"unsupported schema version: {version}")

    @property
    def schema_version(self) -> int:
        return self._db.execute("PRAGMA user_version").fetchone()[0]

    def save_observation(self, observation: Observation) -> str:
        payload = _canonical(observation.model_dump(mode="json"))
        identity = _canonical([
            observation.entity_id, observation.metric, observation.period_end.isoformat(),
            observation.published_at.isoformat(), observation.revision_id, observation.source_id,
        ])
        observation_id = _hash(identity)
        payload_hash = _hash(payload)
        with self._lock:
            existing = self._db.execute(
                "SELECT payload_hash FROM observations WHERE observation_id=?", (observation_id,)
            ).fetchone()
            if existing:
                if existing["payload_hash"] != payload_hash:
                    raise ValueError("conflicting observation identity")
                self._verified_observation(observation_id)
                return observation_id
            # File I/O occurs outside the SQLite write transaction. A crash
            # can leave an orphan file, but can never publish a partial row.
            path = self.store.write_observation(observation)
            file_hash = self.store.checksum(path)
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute(
                    "INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (observation_id, observation.entity_id, observation.metric,
                     observation.period_end.isoformat(), observation.published_at.isoformat(),
                     observation.revision_id, observation.source_id, payload_hash,
                     path.relative_to(self.store.root).as_posix(), file_hash),
                )
                self._db.execute("COMMIT")
            except sqlite3.IntegrityError:
                self._db.execute("ROLLBACK")
                existing = self._db.execute("SELECT payload_hash FROM observations WHERE observation_id=?", (observation_id,)).fetchone()
                if existing and existing["payload_hash"] == payload_hash:
                    return observation_id
                raise ValueError("conflicting observation identity") from None
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
            return observation_id

    def _verified_observation(self, observation_id: str) -> Observation:
        row = self._db.execute("SELECT * FROM observations WHERE observation_id=?", (observation_id,)).fetchone()
        if row is None:
            raise ValueError("unknown observation")
        try:
            path = self.store.resolve(row["file_path"])
            if self.store.checksum(path) != row["file_hash"]:
                raise ValueError("checksum mismatch")
            observation = self.store.read_observation(row["file_path"])
            if _hash(_canonical(observation.model_dump(mode="json"))) != row["payload_hash"]:
                raise ValueError("payload mismatch")
            return observation
        except Exception as exc:
            raise ValueError("missing or invalid observation file") from exc

    def observation_path(self, observation_id: str) -> Path:
        row = self._db.execute("SELECT file_path FROM observations WHERE observation_id=?", (observation_id,)).fetchone()
        if row is None:
            raise ValueError("unknown observation")
        return self.store.resolve(row["file_path"])

    def list_observations(self, entity_id: str, metric: str) -> list[Observation]:
        rows = self._db.execute(
            "SELECT observation_id FROM observations WHERE entity_id=? AND metric=? "
            "ORDER BY period_end, published_at, revision_id", (entity_id, metric)
        ).fetchall()
        return [self._verified_observation(row["observation_id"]) for row in rows]

    def record_job(self, job_id: str, status: str, input_snapshot_id: str) -> bool:
        if not all((job_id, status, input_snapshot_id)):
            raise ValueError("job fields must be nonempty")
        with self._lock:
            existing = self._db.execute("SELECT status, input_snapshot_id FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if existing:
                if (existing["status"], existing["input_snapshot_id"]) != (status, input_snapshot_id):
                    raise ValueError("conflicting job identity")
                return False
            with self._db:
                self._db.execute(
                    "INSERT INTO jobs VALUES (?,?,?,?)",
                    (job_id, status, input_snapshot_id, datetime.now(timezone.utc).isoformat()),
                )
            return True

    def publish_snapshot(
        self, snapshot_id: str, versions: SnapshotVersions, observation_ids: Iterable[str],
        *, before_commit: Callable[[], None] | None = None,
    ) -> Snapshot:
        if not snapshot_id:
            raise ValueError("snapshot_id must be nonempty")
        ids = tuple(sorted(set(observation_ids)))
        if not ids:
            raise ValueError("snapshot requires observations")
        content = _canonical({"versions": versions.model_dump(mode="json"), "observation_ids": ids})
        manifest_id = _hash(content)
        with self._lock:
            existing = self._db.execute(
                "SELECT manifest_id FROM snapshots WHERE snapshot_id=?", (snapshot_id,)
            ).fetchone()
            if existing and existing["manifest_id"] != manifest_id:
                raise ValueError("conflicting snapshot identity")
            observations = tuple(self._verified_observation(key) for key in ids)
            if not existing:
                try:
                    self._db.execute("BEGIN IMMEDIATE")
                    self._db.execute(
                        "INSERT OR IGNORE INTO manifests VALUES (?,?,?,?)",
                        (manifest_id, content, _hash(content), datetime.now(timezone.utc).isoformat()),
                    )
                    self._db.execute(
                        "INSERT INTO snapshots VALUES (?,?,?)",
                        (snapshot_id, manifest_id, datetime.now(timezone.utc).isoformat()),
                    )
                    if before_commit:
                        before_commit()
                    self._db.execute("COMMIT")
                except BaseException:
                    self._db.execute("ROLLBACK")
                    raise
            return Snapshot(snapshot_id, manifest_id, versions, ids, observations)

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        row = self._db.execute(
            "SELECT s.manifest_id, m.content_json, m.content_hash FROM snapshots s "
            "JOIN manifests m ON m.manifest_id=s.manifest_id WHERE s.snapshot_id=?", (snapshot_id,)
        ).fetchone()
        if row is None:
            return None
        content = row["content_json"]
        if _hash(content) != row["content_hash"] or _hash(content) != row["manifest_id"]:
            raise ValueError("invalid snapshot manifest")
        parsed = json.loads(content)
        ids = tuple(parsed["observation_ids"])
        versions = SnapshotVersions.model_validate(parsed["versions"])
        return Snapshot(snapshot_id, row["manifest_id"], versions, ids,
                        tuple(self._verified_observation(key) for key in ids))
