"""Job log as JSON lines with a fixed field set: time, phase, count, error_code.

There is no free-text field, so prompts, amounts and personal data cannot be
logged by accident; error codes are redacted for known secrets and patterns.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from investment_agent.security.redaction import redact


class JobLogger:
    def __init__(self, path: Path, *, secrets: list[str] = ()):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._secrets, self._lock = list(secrets), Lock()

    def event(self, phase: str, *, count: int | None = None, error_code: str | None = None):
        record = {"time": datetime.now(timezone.utc).isoformat(), "phase": phase[:64], "count": count,
                  "error_code": None if error_code is None else redact(error_code, self._secrets)[:200]}
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
