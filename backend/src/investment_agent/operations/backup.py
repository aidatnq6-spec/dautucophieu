"""Local backups: SQLite via the backup API, allowlisted market files, and a personal Firestore export.

Nothing outside the allowlist is copied, so .env files, logs and keys never
enter a backup. Each backup is assembled in a hidden temp directory and
renamed into place, with a manifest of SHA-256 checksums. Retention deletes
only directories directly inside the resolved backup root. Nothing is uploaded.

The owner copies backups to the cloud or an external drive, so with a key the
personal parts (the Firestore export, SQLite files, the watchlist) are written
only as AES-256-GCM ciphertext; no plain copy ever lands in the backup folder.
The key lives in .env.local, which never enters a backup.
"""

import base64
import binascii
import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ALLOWED = (re.compile(r"^prices/[^/]+/(manifest\.json|[^/]+\.parquet)$"), re.compile(r"^documents/.+\.(pdf|html|json)$"),
           re.compile(r"^macro/[a-z0-9_]+\.json$"),  # macro values, including the owner's manual entries
           re.compile(r"^market-symbols\.txt$"))  # the owner's watchlist: edited by hand, nothing can fetch it again
NAME = re.compile(r"^\d{8}T\d{6}Z-(daily|weekly|manual)$")
KEY_ENV = "BACKUP_ENCRYPTION_KEY"
SCHEME = "aes-256-gcm-1"
SUFFIX = ".enc"
_MAGIC, _NONCE = b"IAB1", 12


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


def generate_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def backup_key_from_env() -> bytes | None:
    """None when no key is set; an unusable key is an error, never a reason to write in the clear."""
    raw = os.environ.get(KEY_ENV, "").strip()
    if not raw:
        return None
    try:
        key = base64.urlsafe_b64decode(raw.encode())
    except (binascii.Error, ValueError):
        raise BackupError("backup key is not valid") from None
    if len(key) != 32:
        raise BackupError("backup key is not valid")
    return key


def seal(plain: bytes, key: bytes, label: str) -> bytes:
    """label: the file's place in the backup, bound to the ciphertext so files cannot be swapped."""
    nonce = secrets.token_bytes(_NONCE)
    return _MAGIC + nonce + AESGCM(key).encrypt(nonce, plain, label.encode())


def unseal(blob: bytes, key: bytes, label: str) -> bytes:
    if blob[:len(_MAGIC)] != _MAGIC:
        raise BackupError("not an encrypted backup file")
    start = len(_MAGIC) + _NONCE
    try:
        return AESGCM(key).decrypt(blob[len(_MAGIC):start], blob[start:], label.encode())
    except InvalidTag:
        raise BackupError("wrong backup key or damaged file") from None


def _copy_sqlite(source: Path, target: Path) -> None:
    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)  # consistent committed snapshot even with WAL writers
    finally:
        dst.close()
        src.close()


def export_personal(repo, owner, *, now: datetime) -> dict:
    return {"schema": "personal-export-1", "export_version": "1", "owner_uid": repo.owner_uid, "exported_at": now.isoformat(),
            "documents": repo.export(owner)}


def create_backup(data_dir: Path, backup_root: Path, *, personal_export: dict | None, now: datetime, kind: str, encryption_key: bytes | None = None) -> BackupManifest:
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
            label = f"data/{rel}"
            if source.suffix == ".sqlite":
                target.parent.mkdir(parents=True, exist_ok=True)
                if encryption_key is None:
                    _copy_sqlite(source, target)
                else:
                    with tempfile.TemporaryDirectory(prefix="investment-backup-") as tmp:  # outside the backup folder, which may sync
                        _copy_sqlite(source, Path(tmp) / "copy.sqlite")
                        target.with_name(target.name + SUFFIX).write_bytes(seal((Path(tmp) / "copy.sqlite").read_bytes(), encryption_key, label))
            elif rel == "market-symbols.txt" and encryption_key is not None:
                target.with_name(target.name + SUFFIX).write_bytes(seal(source.read_bytes(), encryption_key, label))
            elif any(p.match(rel) for p in ALLOWED):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        if personal_export is not None:
            text = json.dumps(personal_export, ensure_ascii=False, sort_keys=True).encode("utf-8")
            if encryption_key is None:
                (work / "personal-export.json").write_bytes(text)
            else:
                (work / f"personal-export.json{SUFFIX}").write_bytes(seal(text, encryption_key, "personal-export.json"))
        files = [{"path": p.relative_to(work).as_posix(), "sha256": _sha(p), "size": p.stat().st_size}
                 for p in sorted(work.rglob("*")) if p.is_file()]
        manifest = {"schema": "backup-1", "kind": kind, "created_at": now.isoformat(), "files": files, "personal_export": personal_export is not None, **({"encryption": SCHEME} if encryption_key is not None else {})}
        (work / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(work, final)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    return BackupManifest(path=final, kind=kind, created_at=manifest["created_at"], files=files)


VIETNAM = timezone(timedelta(hours=7))
EVENING_HOUR = 20  # after the last after-close slot, so the day's report is included


def due_backup_kind(backup_root: Path, now: datetime) -> str | None:
    """Kind of scheduled backup due at `now`, or None. At most one per Vietnam day, from the evening
    slot on; a machine that missed an evening catches up at any hour once the last one is a day old.
    Weekly every seven days, daily otherwise. Manual backups do not count."""
    root, today = Path(backup_root), now.astimezone(VIETNAM)
    taken = []
    if root.is_dir():
        for entry in root.iterdir():
            m = NAME.match(entry.name)
            if m and m.group(1) != "manual" and entry.is_dir():
                at = datetime.strptime(entry.name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(VIETNAM)
                taken.append((at, m.group(1)))
    if taken:
        latest = max(at for at, _ in taken)
        if latest.date() == today.date() or (today.hour < EVENING_HOUR and today - latest < timedelta(days=1)):
            return None
    recent_weekly = any(kind == "weekly" and (today.date() - at.date()).days < 7 for at, kind in taken)
    return "daily" if recent_weekly else "weekly"


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
