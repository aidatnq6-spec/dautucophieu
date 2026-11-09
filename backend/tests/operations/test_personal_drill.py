import json
from datetime import datetime, timedelta, timezone

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.operations.backup import BackupError, create_backup, export_personal
from investment_agent.operations.restore import personal_drill
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository, RepositoryUnavailable
from investment_agent.services.system_health import backup_drill

OWNER = OwnerContext("owner-1", "owner", "test")
NOW = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)


def live():
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(OWNER, "settings", "portfolio", {"a": 1}, expected_version=0, request_id="r1")
    repo.write(OWNER, "settings", "portfolio", {"a": 2}, expected_version=1, request_id="r2")
    repo.write(OWNER, "journal", "main", {"entries": []}, expected_version=0, request_id="r3")
    return repo


def backup(repo, tmp_path, *, export=None):
    data = tmp_path / "data"
    (data / "macro").mkdir(parents=True, exist_ok=True)
    (data / "macro" / "wti.json").write_text("{}", encoding="utf-8")
    return create_backup(data, tmp_path / "backups", personal_export=export or export_personal(repo, OWNER, now=NOW), now=NOW, kind="daily").path


class Changed:
    """The live store as seen by the drill, with some documents altered."""
    def __init__(self, repo, change):
        self.repo, self.change, self.owner_uid = repo, change, repo.owner_uid

    def export(self, owner):
        docs = self.repo.export(owner)
        self.change(docs)
        return docs


def path_of(docs, prefix, suffix=""):
    return next(p for p in docs if p.startswith(prefix) and p.endswith(suffix))


def test_a_good_backup_restores_in_full_and_matches_the_live_store(tmp_path):
    repo = live()
    out = personal_drill(backup(repo, tmp_path), repo, OWNER)
    total = len(repo.export(OWNER))
    assert out == {"ok": True, "restored": total, "identical": total, "new_since": 0, "heads_newer": 0, "missing": 0, "differ": 0, "behind": 0, "broken_heads": 0}


def test_what_was_written_after_the_backup_is_counted_and_is_no_fault(tmp_path):
    repo = live()
    path = backup(repo, tmp_path)
    repo.write(OWNER, "settings", "portfolio", {"a": 3}, expected_version=2, request_id="r4")
    out = personal_drill(path, repo, OWNER)
    assert out["ok"] is True and out["heads_newer"] == 1 and out["new_since"] == 2  # the new version and its request; the head moved
    assert out["differ"] == 0 and out["missing"] == 0


def test_a_document_that_differs_from_the_backup_is_a_fault(tmp_path):
    repo = live()
    path = backup(repo, tmp_path)

    def alter(docs):
        docs[path_of(docs, "settings/", "-v1")]["payload"] = {"a": 99}
    out = personal_drill(path, Changed(repo, alter), OWNER)
    assert out["ok"] is False and out["differ"] == 1


def test_a_document_gone_from_the_live_store_is_a_fault(tmp_path):
    repo = live()
    path = backup(repo, tmp_path)
    out = personal_drill(path, Changed(repo, lambda docs: docs.pop(path_of(docs, "journal/"))), OWNER)
    assert out["ok"] is False and out["missing"] == 1


def test_a_live_record_older_than_its_backup_is_a_fault(tmp_path):
    repo = live()
    path = backup(repo, tmp_path)

    def rewind(docs):
        heads = [p for p in docs if p.startswith("record_heads/") and docs[p]["version"] == 2]
        docs[heads[0]] = {"version": 1}
    out = personal_drill(path, Changed(repo, rewind), OWNER)
    assert out["ok"] is False and out["behind"] == 1


def test_a_backup_whose_head_points_at_nothing_is_a_fault(tmp_path):
    repo = live()
    export = export_personal(repo, OWNER, now=NOW)
    export["documents"].pop(path_of(export["documents"], "journal/"))
    out = personal_drill(backup(repo, tmp_path, export=export), repo, OWNER)
    assert out["ok"] is False and out["broken_heads"] == 1


def test_a_backup_of_another_owner_is_refused(tmp_path):
    repo = live()
    export = export_personal(repo, OWNER, now=NOW)
    export["owner_uid"] = "owner-2"
    with pytest.raises(BackupError):
        personal_drill(backup(repo, tmp_path, export=export), repo, OWNER)


def data_dir(tmp_path):
    (tmp_path / "live").mkdir(exist_ok=True)
    return tmp_path / "live"


def test_the_weekly_drill_keeps_only_counts_of_the_personal_check(tmp_path):
    repo = live()
    backup(repo, tmp_path)
    out = backup_drill(tmp_path / "backups", data_dir(tmp_path), now=NOW, repo=repo, owner=OWNER)
    assert out["ok"] is True and out["personal"]["ok"] is True and out["personal"]["missing"] == 0
    text = (data_dir(tmp_path) / "alerts" / "restore-drill.json").read_text(encoding="utf-8")
    assert json.loads(text)["personal"]["restored"] > 0 and "portfolio" not in text and "payload" not in text


def test_a_mismatch_fails_the_drill(tmp_path):
    repo = live()
    backup(repo, tmp_path)
    changed = Changed(repo, lambda docs: docs.pop(path_of(docs, "journal/")))
    out = backup_drill(tmp_path / "backups", data_dir(tmp_path), now=NOW, repo=changed, owner=OWNER)
    assert out["ok"] is False and out["error"] == "PersonalMismatch"


def test_firestore_being_out_of_reach_says_so_and_does_not_condemn_the_backup(tmp_path):
    class Down:
        owner_uid = "owner-1"

        def export(self, owner):
            raise RepositoryUnavailable("down")
    backup(live(), tmp_path)
    out = backup_drill(tmp_path / "backups", data_dir(tmp_path), now=NOW, repo=Down(), owner=OWNER)
    assert out["ok"] is True and out["personal"] == "unavailable"


def test_force_runs_a_drill_that_is_not_due(tmp_path):
    repo = live()
    backup(repo, tmp_path)
    assert backup_drill(tmp_path / "backups", data_dir(tmp_path), now=NOW, repo=repo, owner=OWNER)["status"] == "done"
    later = NOW + timedelta(days=1)
    assert backup_drill(tmp_path / "backups", data_dir(tmp_path), now=later, repo=repo, owner=OWNER)["status"] == "not_due"
    assert backup_drill(tmp_path / "backups", data_dir(tmp_path), now=later, repo=repo, owner=OWNER, force=True)["status"] == "done"
