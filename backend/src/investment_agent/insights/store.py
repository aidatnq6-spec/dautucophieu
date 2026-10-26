"""One JSON per processed report under data/insights/reports (no PDFs or full texts are kept)."""

import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

_ID = re.compile(r"^[A-Za-z0-9_-]{1,120}$")


class InsightStore:
    def __init__(self, root: Path):
        self.root = Path(root) / "reports"

    def _path(self, source: str, ref_id: str) -> Path:
        if not (_ID.fullmatch(source) and _ID.fullmatch(ref_id)):
            raise ValueError("invalid report id")
        return self.root / f"{source}-{ref_id}.json"

    def read(self, source: str, ref_id: str) -> dict | None:
        p = self._path(source, ref_id)
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    def save(self, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        p = self._path(record["source"], record["ref_id"])
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, p)

    def all(self) -> list[dict]:
        if not self.root.is_dir():
            return []
        out = [json.loads(p.read_text(encoding="utf-8")) for p in self.root.glob("*.json")]
        return sorted(out, key=lambda r: r["published"], reverse=True)

    def recent(self, today: date, *, days: int = 60) -> list[dict]:
        cutoff = (today - timedelta(days=days)).isoformat()
        return [r for r in self.all() if r["published"] >= cutoff]
