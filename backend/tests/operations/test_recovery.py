import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.operations.backup import BackupError, create_backup, export_personal, prune_backups
from investment_agent.operations.logging import JobLogger
from investment_agent.operations.restore import BackupCorrupt, preview_personal_restore, restore_local, restore_personal, verify_backup
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

OWNER = OwnerContext("owner-1", "owner", "backup")
NOW = datetime(2026, 10, 25, 2, tzinfo=timezone.utc)
SECRET = "sk-or-v1-" + "s" * 40


@pytest.fixture
def data(tmp_path):
    d = tmp_path / "data"
    (d / "prices" / "FPT").mkdir(parents=True)
    (d / "prices" / "FPT" / "manifest.json").write_text('{"revisions": []}', encoding="utf-8")
    db = sqlite3.connect(d / "jobs.sqlite")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE t (v TEXT)")
    db.execute("INSERT INTO t VALUES ('committed')")
    db.commit()
    (d / ".env.local").write_text(f"OPENROUTER_API_KEY={SECRET}", encoding="utf-8")
    (d / "scheduler.log").write_text(f"token {SECRET}", encoding="utf-8")
    yield d, db
    db.close()


def repo_with_records():
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(OWNER, "ledger_events", "main", {"schema_version": "2", "events": [{"event_id": "d1"}], "amendments": [], "changes": []},
               expected_version=0, request_id="l1")
    repo.write(OWNER, "reports", "ab" * 16, {"report_id": "ab" * 16, "status": "published"}, expected_version=0, request_id="r1")
    return repo


def test_sqlite_backup_is_consistent_while_wal_is_open(data, tmp_path):
    d, db = data
    db.execute("INSERT INTO t VALUES ('uncommitted')")  # open write transaction, not committed
    manifest = create_backup(d, tmp_path / "backups", personal_export=None, now=NOW, kind="daily")
    copy = sqlite3.connect(manifest.path / "data" / "jobs.sqlite")
    assert copy.execute("SELECT v FROM t").fetchall() == [("committed",)]
    copy.close()


def test_backup_excludes_secrets_and_logs(data, tmp_path):
    d, _ = data
    manifest = create_backup(d, tmp_path / "backups", personal_export=None, now=NOW, kind="daily")
    names = {f["path"] for f in manifest.files}
    assert "data/jobs.sqlite" in names and "data/prices/FPT/manifest.json" in names
    assert not any(".env" in n or n.endswith(".log") for n in names)
    for path in manifest.path.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()


def test_corrupted_backup_is_not_restored(data, tmp_path):
    d, _ = data
    manifest = create_backup(d, tmp_path / "backups", personal_export=None, now=NOW, kind="daily")
    (manifest.path / "data" / "prices" / "FPT" / "manifest.json").write_text("tampered", encoding="utf-8")
    with pytest.raises(BackupCorrupt):
        verify_backup(manifest.path)
    target = tmp_path / "restore"
    with pytest.raises(BackupCorrupt):
        restore_local(manifest.path, target)
    assert not target.exists()


def test_restore_into_fresh_directory_reproduces_files(data, tmp_path):
    d, _ = data
    manifest = create_backup(d, tmp_path / "backups", personal_export=None, now=NOW, kind="daily")
    target = tmp_path / "restore"
    restore_local(manifest.path, target)
    assert (target / "prices" / "FPT" / "manifest.json").read_text(encoding="utf-8") == '{"revisions": []}'
    with pytest.raises(BackupError):
        restore_local(manifest.path, target)  # never into a non-empty directory


def test_personal_export_round_trips_into_empty_store_and_matches(data, tmp_path):
    d, _ = data
    source = repo_with_records()
    export = export_personal(source, OWNER, now=NOW)
    assert export["owner_uid"] == "owner-1" and export["export_version"] == "1"
    manifest = create_backup(d, tmp_path / "backups", personal_export=export, now=NOW, kind="daily")
    target = PersonalRepository("owner-1", MemoryDocumentStore())
    preview = preview_personal_restore(manifest.path, target, OWNER)
    assert preview.to_create > 0 and preview.conflicts == 0
    restore_personal(manifest.path, target, OWNER, confirm=True)
    assert target.read(OWNER, "ledger_events", "main").payload == source.read(OWNER, "ledger_events", "main").payload
    assert target.read(OWNER, "reports", "ab" * 16).payload["status"] == "published"


def test_personal_restore_never_overwrites_newer_data_silently(data, tmp_path):
    d, _ = data
    source = repo_with_records()
    manifest = create_backup(d, tmp_path / "backups", personal_export=export_personal(source, OWNER, now=NOW), now=NOW, kind="daily")
    head = source.read(OWNER, "ledger_events", "main")
    source.write(OWNER, "ledger_events", "main", {**head.payload, "events": []}, expected_version=1, request_id="l2")
    preview = preview_personal_restore(manifest.path, source, OWNER)
    assert preview.conflicts >= 1
    with pytest.raises(BackupError):
        restore_personal(manifest.path, source, OWNER, confirm=True)
    assert source.read(OWNER, "ledger_events", "main").version == 2
    with pytest.raises(BackupError):
        restore_personal(manifest.path, PersonalRepository("owner-1", MemoryDocumentStore()), OWNER, confirm=False)


def test_export_of_other_owner_is_refused(data, tmp_path):
    d, _ = data
    manifest = create_backup(d, tmp_path / "backups", personal_export=export_personal(repo_with_records(), OWNER, now=NOW), now=NOW, kind="daily")
    other = OwnerContext("owner-2", "owner", "x")
    with pytest.raises(Exception):
        preview_personal_restore(manifest.path, PersonalRepository("owner-2", MemoryDocumentStore()), other)


def test_retention_keeps_7_daily_4_weekly_and_stays_inside_root(data, tmp_path):
    d, _ = data
    root = tmp_path / "backups"
    for i in range(10):
        create_backup(d, root, personal_export=None, now=NOW - timedelta(days=i), kind="daily")
    for i in range(6):
        create_backup(d, root, personal_export=None, now=NOW - timedelta(weeks=i, hours=1), kind="weekly")
    outside = tmp_path / "keep-me"
    outside.mkdir()
    removed = prune_backups(root, keep_daily=7, keep_weekly=4)
    kinds = sorted(p.name.rsplit("-", 1)[1] for p in root.iterdir())
    assert kinds.count("daily") == 7 and kinds.count("weekly") == 4 and len(removed) == 5
    assert outside.exists() and all(p.parent == root.resolve() for p in removed)


def test_job_log_records_only_safe_fields(tmp_path, caplog):
    log = JobLogger(tmp_path / "jobs.log", secrets=[SECRET])
    log.event("publish", count=3, error_code=None)
    log.event("narrate", error_code=f"failed {SECRET}")
    with pytest.raises(TypeError):
        log.event("compose", prompt="Thu nhập 50 triệu")
    lines = [json.loads(l) for l in (tmp_path / "jobs.log").read_text(encoding="utf-8").splitlines()]
    assert set(lines[0]) == {"time", "phase", "count", "error_code"} and SECRET not in (tmp_path / "jobs.log").read_text(encoding="utf-8")
