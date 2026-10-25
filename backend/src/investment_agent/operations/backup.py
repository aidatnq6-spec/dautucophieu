"""Local backups: SQLite via the backup API, allowlisted market files, and a personal Firestore export.

Nothing outside the allowlist is copied, so .env files, logs and keys never
enter a backup. Each backup is assembled in a hidden temp directory and
renamed into place, with a manifest of SHA-256 checksums. Retention deletes
only directories directly inside the resolved backup root. Nothing is uploaded.
"""

import hashlib
import json
import os
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ALLOWED = (re.compile(r"^prices/[^/]+/(manifest\.json|[^/]+\.parquet)$"), re.compile(r"^documents/.+\.(pdf|html|json)$"))
NAME = re.compile(r"^\d{8}T\d{6}Z-(daily|weekly|manual)$")


class BackupError(Exception):
    pass


@dataclass(frozen=True)
class BackupManifest:
    path: Path
    kind: str
    created_at: str
    files: list[dict]


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def export_personal(repo, owner, *, now: datetime) -> dict:
    return {"schema": "personal-export-1", "export_version": "1", "owner_uid": repo.owner_uid, "exported_at": now.isoformat(),
            "documents": repo.export(owner)}


def create_backup(data_dir: Path, backup_root: Path, *, personal_export: dict | None, now: datetime, kind: str) -> BackupManifest:
    if kind not in {"daily", "weekly", "manual"}:
        raise BackupError("unknown backup kind")
    data_dir, root = Path(data_dir).resolve(), Path(backup_root).resolve()
    name = f"{now:%Y%m%dT%H%M%SZ}-{kind}"
    final, work = root / name, root / f".partial-{name}"
    if final.exists():
        raise BackupError("backup already exists")
    shutil.rmtree(work, ignore_errors=True)
    (work / "data").mkdir(parents=True)
    try:
        for source in sorted(data_dir.rglob("*")):
            if not source.is_file() or source.is_symlink():
                continue
            rel = source.relative_to(data_dir).as_posix()
            target = work / "data" / rel
            if source.suffix == ".sqlite":
                target.parent.mkdir(parents=True, exist_ok=True)
                src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
                dst = sqlite3.connect(target)
                try:
                    src.backup(dst)  # consistent committed snapshot even with WAL writers
                finally:
                    dst.close()
                    src.close()
            elif any(p.match(rel) for p in ALLOWED):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        if personal_export is not None:
            (work / "personal-export.json").write_text(json.dumps(personal_export, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        files = [{"path": p.relative_to(work).as_posix(), "sha256": _sha(p), "size": p.stat().st_size}
                 for p in sorted(work.rglob("*")) if p.is_file()]
        manifest = {"schema": "backup-1", "kind": kind, "created_at": now.isoformat(), "files": files, "personal_export": personal_export is not None}
        (work / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(work, final)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    return BackupManifest(path=final, kind=kind, created_at=manifest["created_at"], files=files)


def prune_backups(backup_root: Path, *, keep_daily: int = 7, keep_weekly: int = 4) -> list[Path]:
    root = Path(backup_root).resolve()
    keep = {"daily": keep_daily, "weekly": keep_weekly, "manual": 10**6}
    groups: dict[str, list[Path]] = {}
    for entry in root.iterdir():
        m = NAME.match(entry.name)
        if m and entry.is_dir() and not entry.is_symlink():
            groups.setdefault(m.group(1), []).append(entry)
    removed = []
    for kind, entries in groups.items():
        for entry in sorted(entries, key=lambda p: p.name, reverse=True)[keep[kind]:]:
            real = Path(os.path.realpath(entry))
            if real.parent != root:  # junctions or links pointing elsewhere are never followed
                continue
            shutil.rmtree(real)
            removed.append(real)
    return removed
