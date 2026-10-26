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
        """Every readable record, newest first; a corrupt or partial file is skipped rather than breaking the page or run."""
        out = []
        for p in sorted(self.root.glob("*.json")) if self.root.is_dir() else []:
            try:
                record = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(record, dict) and isinstance(record.get("published"), str) and record.get("source") and record.get("ref_id"):
                out.append(record)
        return sorted(out, key=lambda r: r["published"], reverse=True)

    @property
    def _failures_path(self) -> Path:
        return self.root.parent / "failures.json"

    def failures(self) -> dict[str, dict]:
        try:
            data = json.loads(self._failures_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def record_failure(self, key: str, code: str, at: str) -> int:
        data = self.failures()
        attempts = int((data.get(key) or {}).get("attempts", 0)) + 1
        data[key] = {"attempts": attempts, "last_error": code, "at": at}
        self._failures_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._failures_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._failures_path)
        return attempts

    def recent(self, today: date, *, days: int = 60) -> list[dict]:
        cutoff = (today - timedelta(days=days)).isoformat()
        return [r for r in self.all() if r["published"] >= cutoff]
