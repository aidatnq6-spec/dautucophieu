import base64
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.operations.backup import BackupError, backup_key_from_env, create_backup, export_personal, generate_key
from investment_agent.operations.restore import BackupCorrupt, personal_drill, read_personal_export, restore_local, verify_backup
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.system_health import backup_drill

NOW = datetime(2026, 11, 9, 13, 0, tzinfo=timezone.utc)
OWNER = OwnerContext("owner-1", "owner", "test")
KEY = base64.urlsafe_b64decode(generate_key())
SECRET = "SO-LIEU-RIENG-123456789"


@pytest.fixture
def repo():
    r = PersonalRepository("owner-1", MemoryDocumentStore())
    r.write(OWNER, "journal", "main", {"note": SECRET}, expected_version=0, request_id="j1")
    return r


@pytest.fixture
def data(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "market-symbols.txt").write_text(f"{SECRET}\n", encoding="utf-8")
    db = sqlite3.connect(d / "jobs.sqlite")
    db.execute("create table t(v text)")
    db.execute("insert into t values (?)", (SECRET,))
    db.commit()
    db.close()
    (d / "macro").mkdir()
    (d / "macro" / "cpi.json").write_text("{}", encoding="utf-8")
    return d


def backup(data, tmp_path, repo, key=KEY):
    return create_backup(data, tmp_path / "backups", personal_export=export_personal(repo, OWNER, now=NOW), now=NOW, kind="daily", encryption_key=key).path


def test_nothing_personal_is_readable_in_the_backup(data, tmp_path, repo):
    path = backup(data, tmp_path, repo)
    names = {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}
    assert {"personal-export.json.enc", "data/jobs.sqlite.enc", "data/market-symbols.txt.enc"} <= names
    assert not {"personal-export.json", "data/jobs.sqlite", "data/market-symbols.txt"} & names
    for p in path.rglob("*"):
        if p.is_file():
            assert SECRET.encode() not in p.read_bytes(), p.name
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["encryption"] == "aes-256-gcm-1" and manifest["personal_export"] is True


def test_checksums_can_be_checked_without_the_key(data, tmp_path, repo):
    assert verify_backup(backup(data, tmp_path, repo))["kind"] == "daily"


def test_with_the_key_everything_comes_back(data, tmp_path, repo):
    path = backup(data, tmp_path, repo)
    target = tmp_path / "restored"
    restored = restore_local(path, target, key=KEY)
    assert "data/jobs.sqlite" in restored and (target / "market-symbols.txt").read_text(encoding="utf-8") == f"{SECRET}\n"
    assert sqlite3.connect(target / "jobs.sqlite").execute("select v from t").fetchone() == (SECRET,)
    assert read_personal_export(path, key=KEY)["owner_uid"] == "owner-1"


def test_no_key_or_a_wrong_key_opens_nothing(data, tmp_path, repo, monkeypatch):
    monkeypatch.delenv("BACKUP_ENCRYPTION_KEY", raising=False)
    path = backup(data, tmp_path, repo)
    with pytest.raises(BackupError):
        read_personal_export(path)
    with pytest.raises(BackupError):
        read_personal_export(path, key=b"0" * 32)
    target = tmp_path / "wrong"
    with pytest.raises(BackupError):
        restore_local(path, target, key=b"0" * 32)


def test_files_cannot_be_swapped_inside_a_backup(data, tmp_path, repo):
    path = backup(data, tmp_path, repo)
    (path / "personal-export.json.enc").write_bytes((path / "data" / "jobs.sqlite.enc").read_bytes())
    with pytest.raises(BackupCorrupt):  # the checksum catches it first
        verify_backup(path)


def test_the_key_comes_from_the_environment_and_a_bad_one_is_refused(monkeypatch):
    monkeypatch.delenv("BACKUP_ENCRYPTION_KEY", raising=False)
    assert backup_key_from_env() is None
    good = generate_key()
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", good)
    assert backup_key_from_env() == base64.urlsafe_b64decode(good)
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "ngan-qua")
    with pytest.raises(BackupError):
        backup_key_from_env()


def test_the_drill_and_personal_compare_read_an_encrypted_backup_using_the_environment(data, tmp_path, repo, monkeypatch):
    key = generate_key()
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", key)
    path = backup(data, tmp_path, repo, key=base64.urlsafe_b64decode(key))
    assert personal_drill(path, repo, OWNER)["ok"] is True
    out = backup_drill(tmp_path / "backups", data, now=NOW + timedelta(days=1), repo=repo, owner=OWNER, force=True)
    assert out["ok"] is True and out["files"] >= 2 and out["personal"]["ok"] is True


def test_the_drill_reports_a_missing_key_as_a_failure(data, tmp_path, repo, monkeypatch):
    backup(data, tmp_path, repo)
    monkeypatch.delenv("BACKUP_ENCRYPTION_KEY", raising=False)
    out = backup_drill(tmp_path / "backups", data, now=NOW + timedelta(days=1), force=True)
    assert out["ok"] is False and out["error"]


def test_older_backups_without_encryption_still_restore(data, tmp_path, repo):
    path = create_backup(data, tmp_path / "backups", personal_export=export_personal(repo, OWNER, now=NOW), now=NOW, kind="daily").path
    assert (path / "personal-export.json").is_file()
    assert read_personal_export(path)["owner_uid"] == "owner-1"
    assert "data/jobs.sqlite" in restore_local(path, tmp_path / "old")


def test_the_scheduled_command_writes_no_backup_without_a_key(tmp_path, monkeypatch, capsys):
    from investment_agent import cli
    monkeypatch.delenv("BACKUP_ENCRYPTION_KEY", raising=False)
    (tmp_path / "data").mkdir()
    monkeypatch.setattr("sys.argv", ["cli", "backup", "--data-dir", str(tmp_path / "data"), "--backup-dir", str(tmp_path / "backups"), "--kind", "manual"])
    assert cli.main() == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "backup_key_missing"
    assert not (tmp_path / "backups").exists() or not list((tmp_path / "backups").iterdir())
