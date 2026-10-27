"""Close series keyed by timestamp, one JSON file per key (e.g. "FPT-1h", "BTC-1d").

Values are kept as decimal strings and read back as floats for indicator math. A newer value at
the same timestamp replaces the older one; only the latest `keep` points are retained.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

_KEY = re.compile(r"^[A-Za-z0-9_-]{1,60}$")


class SeriesStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        if not _KEY.fullmatch(key):
            raise ValueError("invalid series key")
        return self.root / f"{key}.json"

    def read(self, key: str) -> list[tuple[datetime, float]]:
        path = self._path(key)
        if not path.is_file():
            return []
        return [(datetime.fromisoformat(t), float(v)) for t, v in json.loads(path.read_text(encoding="utf-8"))["points"]]

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
