"""Close series keyed by timestamp, one JSON file per key (e.g. "FPT-1h", "BTC-1d").

Values are kept as decimal strings and read back as floats for indicator math. A newer value at
the same timestamp replaces the older one; only the latest `keep` points are retained.
"""

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path

_KEY = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
_PARSED: dict[str, tuple[tuple[int, int], list, list]] = {}  # path -> ((mtime_ns, size), points as written, points as read)
_PARSED_MAX = 600
_PARSED_LOCK = threading.Lock()


def _parsed(path: Path) -> tuple[list, list] | None:
    """The file's points, parsed once per version of the file: kept while its modification time and size are unchanged, so a
    page reading sixty series no longer decodes sixty files on every request. None when the file does not exist."""
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    stamp, key = (st.st_mtime_ns, st.st_size), str(path)
    with _PARSED_LOCK:
        hit = _PARSED.get(key)
    if hit and hit[0] == stamp:
        return hit[1], hit[2]
    raw = [tuple(p) for p in json.loads(path.read_text(encoding="utf-8"))["points"]]
    read = [(datetime.fromisoformat(t), float(v)) for t, v in raw]
    with _PARSED_LOCK:
        _PARSED[key] = (stamp, raw, read)
        while len(_PARSED) > _PARSED_MAX:
            _PARSED.pop(next(iter(_PARSED)))
    return raw, read


class SeriesStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        if not _KEY.fullmatch(key):
            raise ValueError("invalid series key")
        return self.root / f"{key}.json"

    def read(self, key: str) -> list[tuple[datetime, float]]:
        parsed = _parsed(self._path(key))
        return list(parsed[1]) if parsed else []  # a new list each time: callers may change it, the tuples cannot be

    def points(self, key: str) -> list[tuple[str, str]]:
        """The stored (timestamp, decimal string) pairs as written, oldest first."""
        parsed = _parsed(self._path(key))
        return list(parsed[0]) if parsed else []

    def replace(self, key: str, points: list[tuple[datetime, str]]) -> None:
        """The series becomes exactly these points (a rebuild from new sources); upsert keeps old days the new points lack."""
        path = self._path(key)
        if path.is_file():
            path.unlink()
        self.upsert(key, points)

    def upsert(self, key: str, points: list[tuple[datetime, str]], *, keep: int = 9000) -> None:  # ~36 years of sessions (full history for drawdowns)
        path = self._path(key)
        merged = {t: v for t, v in (json.loads(path.read_text(encoding="utf-8"))["points"] if path.is_file() else [])}
        for t, v in points:
            stamp = t.date().isoformat() if key.endswith("-1d") else t.isoformat()
            merged[stamp] = str(v)
        ordered = sorted(merged.items(), key=lambda kv: datetime.fromisoformat(kv[0]))[-keep:]
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"key": key, "points": ordered}), encoding="utf-8")
        os.replace(tmp, path)
