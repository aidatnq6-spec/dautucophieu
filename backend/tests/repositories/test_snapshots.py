from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3

import pytest
import pyarrow.parquet as pq

from investment_agent.domain.models import Observation, SnapshotVersions
from investment_agent.market.parquet_store import ParquetStore
from investment_agent.repositories.sqlite import LocalRepository


def observation(revision: str, value: str | None = "123.45") -> Observation:
    return Observation(
        entity_id="entity-1", metric="revenue", period_end="2025-12-31",
        published_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        observed_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
        revision_id=revision, source_id="source-1", unit="VND",
        value=value, quality_status="verified" if value is not None else "missing",
        provenance_mode="historical_as_reported",
        missing_reason=None if value is not None else "not disclosed",
    )


def versions(data_revision: str = "r2") -> SnapshotVersions:
    return SnapshotVersions(
        profile_version="p1", portfolio_version="pf1", universe_version="u1",
        data_revision_id=data_revision, assumption_version="a1", policy_version="pol1",
    )


def test_revisions_are_preserved_and_retry_is_idempotent(tmp_path: Path):
    with LocalRepository(tmp_path / "catalog.sqlite", ParquetStore(tmp_path / "data")) as repo:
        first = repo.save_observation(observation("r1", "123.45"))
        second = repo.save_observation(observation("r2", "124.50"))
        assert first != second
        assert repo.save_observation(observation("r1", "123.45")) == first
        rows = repo.list_observations("entity-1", "revenue")
        assert [(row.revision_id, row.value) for row in rows] == [
            ("r1", Decimal("123.45")), ("r2", Decimal("124.50"))]
        with pytest.raises(ValueError, match="conflicting observation"):
            repo.save_observation(observation("r1", "999"))
        assert len(repo.list_observations("entity-1", "revenue")) == 2
        raw_value = pq.read_table(repo.observation_path(first)).to_pylist()[0]["value"]
        assert raw_value == "123.45"


def test_missing_value_roundtrips_as_null_with_reason(tmp_path: Path):
    with LocalRepository(tmp_path / "catalog.sqlite", ParquetStore(tmp_path / "data")) as repo:
        repo.save_observation(observation("missing", None))
        row = repo.list_observations("entity-1", "revenue")[0]
        assert row.value is None
        assert row.missing_reason == "not disclosed"
        assert pq.read_table(repo.observation_path(repo.save_observation(observation("missing", None)))).to_pylist()[0]["value"] is None


def test_file_paths_are_generated_and_conflicting_existing_file_fails(tmp_path: Path):
    store = ParquetStore(tmp_path / "data")
    with pytest.raises(ValueError, match="invalid observation path"):
        store.resolve("../outside.parquet")
    dangerous = observation("../../revision")
    path = store.write_observation(dangerous)
    assert path.parent == store.root
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="existing observation file"):
        store.write_observation(dangerous)


def test_failed_publish_and_orphan_do_not_appear_after_reopen(tmp_path: Path):
    db = tmp_path / "catalog.sqlite"
    store = ParquetStore(tmp_path / "data")
    with LocalRepository(db, store) as repo:
        first = repo.save_observation(observation("r1"))
        repo.publish_snapshot("snap-1", versions("r1"), [first])
        second = repo.save_observation(observation("r2", "124.50"))
        with pytest.raises(RuntimeError, match="simulated crash"):
            repo.publish_snapshot("snap-2", versions(), [second], before_commit=lambda: (_ for _ in ()).throw(RuntimeError("simulated crash")))
        assert repo.get_snapshot("snap-2") is None
        orphan = store.write_observation(observation("orphan", "999"))
        assert orphan.exists()
    with LocalRepository(db, store) as repo:
        saved = repo.get_snapshot("snap-1")
        assert saved is not None
        assert saved.observations[0].value == Decimal("123.45")
        assert repo.get_snapshot("snap-2") is None
        assert {row.revision_id for row in repo.list_observations("entity-1", "revenue")} == {"r1", "r2"}


def test_manifest_requires_valid_files_and_immutable_snapshot_id(tmp_path: Path):
    store = ParquetStore(tmp_path / "data")
    with LocalRepository(tmp_path / "catalog.sqlite", store) as repo:
        key = repo.save_observation(observation("r1"))
        initial = repo.publish_snapshot("snap-1", versions("r1"), [key])
        assert repo.publish_snapshot("snap-1", versions("r1"), [key]) == initial
        with pytest.raises(ValueError, match="conflicting snapshot"):
            repo.publish_snapshot("snap-1", versions(), [key])
        path = repo.observation_path(key)
        path.unlink()
        with pytest.raises(ValueError, match="missing or invalid"):
            repo.get_snapshot("snap-1")
        with pytest.raises(ValueError, match="missing or invalid"):
            repo.publish_snapshot("snap-3", versions(), [key])


def test_schema_version_and_job_retry(tmp_path: Path):
    with LocalRepository(tmp_path / "catalog.sqlite", ParquetStore(tmp_path / "data")) as repo:
        assert repo.schema_version == 1
        assert repo.record_job("job-1", "running", "snapshot-1") is True
        assert repo.record_job("job-1", "running", "snapshot-1") is False
        with pytest.raises(ValueError, match="conflicting job"):
            repo.record_job("job-1", "running", "snapshot-2")


def test_published_catalog_rows_are_immutable(tmp_path: Path):
    db = tmp_path / "catalog.sqlite"
    with LocalRepository(db, ParquetStore(tmp_path / "data")) as repo:
        key = repo.save_observation(observation("r1"))
        repo.publish_snapshot("snap-1", versions("r1"), [key])
    with sqlite3.connect(db) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE observations SET revision_id='changed'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("DELETE FROM manifests")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("DELETE FROM snapshots")
