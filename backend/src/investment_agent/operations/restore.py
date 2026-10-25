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
