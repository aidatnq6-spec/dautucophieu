"""Versioned policy files pinned by a digest of their parsed content."""

import hashlib
import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"


class InvalidPolicy(ValueError):
    pass


def content_digest(data) -> str:
    # Parsed content, so Git line-ending conversion cannot change the digest.
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_pinned(path: Path, pins: dict[str, str]) -> tuple[dict, str]:
    """Return (data, digest); an edited file must ship under a new version key."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InvalidPolicy("Policy file unreadable") from exc
    digest = content_digest(data)
    if not isinstance(data, dict) or pins.get(data.get("version")) != digest:
        raise InvalidPolicy("Policy content does not match its pinned version")
    return data, digest
