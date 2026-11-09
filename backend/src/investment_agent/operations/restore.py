"""Restore after checksum verification: local files into a new empty directory;
personal records only after a preview, creating missing documents and refusing
when any existing document differs (no silent overwrite of newer data)."""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .backup import BackupError, _sha


class BackupCorrupt(BackupError):
    pass


@dataclass(frozen=True)
class RestorePreview:
    to_create: int
    identical: int
    conflicts: int


def verify_backup(path: Path) -> dict:
    path = Path(path)
    try:
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BackupCorrupt("manifest unreadable") from None
    for f in manifest["files"]:
        target = path / f["path"]
        if not target.is_file() or target.stat().st_size != f["size"] or _sha(target) != f["sha256"]:
            raise BackupCorrupt(f"checksum mismatch: {f['path']}")
    return manifest


def restore_local(path: Path, target: Path) -> list[str]:
    manifest = verify_backup(path)
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        raise BackupError("restore target must be empty")
    restored = []
    for f in manifest["files"]:
        if not f["path"].startswith("data/"):
            continue
        dest = target / f["path"][len("data/"):]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(path) / f["path"], dest)
        restored.append(f["path"])
    return restored


def _export(path: Path, repo) -> dict:
    manifest = verify_backup(path)
    if not manifest.get("personal_export"):
        raise BackupError("backup has no personal export")
    export = json.loads((Path(path) / "personal-export.json").read_text(encoding="utf-8"))
    if export.get("schema") != "personal-export-1" or export.get("owner_uid") != repo.owner_uid:
        raise BackupError("export belongs to another owner or schema")
    return export


def preview_personal_restore(path: Path, repo, owner) -> RestorePreview:
    export = _export(path, repo)
    return RestorePreview(*repo.import_documents(owner, export["documents"], dry_run=True))


def restore_personal(path: Path, repo, owner, *, confirm: bool) -> RestorePreview:
    if not confirm:
        raise BackupError("restore needs explicit confirmation after preview")
    preview = preview_personal_restore(path, repo, owner)
    if preview.conflicts:
        raise BackupError("existing records differ from the backup; resolve manually before restoring")
    export = _export(path, repo)
    return RestorePreview(*repo.import_documents(owner, export["documents"], dry_run=False))


def personal_drill(path: Path, live, owner) -> dict:
    """Restore a backup's personal export into an empty store in memory and compare it with the live one; nothing is written to the live store and only
    counts come back. Records are append-only, so anything the backup holds must still be there unchanged; only a record's head may have moved on.
    missing, differ and behind are faults, as is broken_heads: a head in the backup with no revision for it."""
    from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

    restored_repo = PersonalRepository(live.owner_uid, MemoryDocumentStore())
    restore_personal(path, restored_repo, owner, confirm=True)
    restored, current = restored_repo.export(owner), live.export(owner)
    heads = {p: d for p, d in restored.items() if p.startswith("record_heads/")}
    missing = sum(1 for p in restored if p not in current)
    differ = sum(1 for p, d in restored.items() if p in current and p not in heads and current[p] != d)
    behind = sum(1 for p, d in heads.items() if p in current and current[p]["version"] < d["version"])
    heads_newer = sum(1 for p, d in heads.items() if p in current and current[p]["version"] > d["version"])
    identical = sum(1 for p, d in restored.items() if current.get(p) == d)
    suffixes = {p.rsplit("/", 1)[-1] for p in restored if not p.startswith("record_heads/")}
    broken = sum(1 for p, d in heads.items() if f"{p.rsplit('/', 1)[-1]}-v{d['version']}" not in suffixes)
    return {"ok": not (missing or differ or behind or broken), "restored": len(restored), "identical": identical, "new_since": sum(1 for p in current if p not in restored),
            "heads_newer": heads_newer, "missing": missing, "differ": differ, "behind": behind, "broken_heads": broken}

