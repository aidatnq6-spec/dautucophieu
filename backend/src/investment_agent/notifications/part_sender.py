"""Telegram notes in parts that are never sent twice.

A long note is split into numbered parts sent in order. If a part after the first fails, the parts not yet sent are kept in a small
local file and the note counts as delivered: the next send (this run or a later one) sends those parts first, then its own note.
A note whose first part fails sends nothing and reports failure, so its caller retries it whole. A new note never overtakes
parts still waiting, so the chat keeps the order."""

import json
import os
from collections.abc import Callable
from pathlib import Path

from investment_agent.notifications.render import split_message


class PartSender:
    def __init__(self, send_part: Callable[[str], bool], pending_path: Path):
        self.send_part, self.path = send_part, Path(pending_path)

    def _pending(self) -> list[str]:
        try:
            parts = json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else []
        except (OSError, ValueError):
            parts = []  # unreadable: set aside rather than block every note
        return [p for p in parts if isinstance(p, str)] if isinstance(parts, list) else []

    def _keep(self, parts: list[str]) -> None:
        if not parts:
            self.path.unlink(missing_ok=True)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(parts, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def _send(self, parts: list[str]) -> int:
        """How many parts went out, in order, stopping at the first failure."""
        for i, part in enumerate(parts):
            if not self.send_part(part):
                return i
        return len(parts)

    def __call__(self, text: str) -> bool:
        waiting = self._pending()
        if waiting:
            done = self._send(waiting)
            self._keep(waiting[done:])
            if done < len(waiting):
                return False
        parts = split_message(text)
        done = self._send(parts)
        if done == 0:
            return False
        self._keep(parts[done:])
        return True
