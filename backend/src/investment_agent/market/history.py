"""Full daily history for drawdowns: a series is filled backwards, one source window at a time (Vnstock returns about eight years
per request), until the source has nothing older. Done once per series; later runs only add new sessions as before."""

import json
import os
from datetime import date, timedelta
from pathlib import Path

from .series import SeriesStore

MARKER = "_history.json"
MAX_WINDOWS = 5  # ~40 years at eight years a window; VN-Index starts in 2000


def _marks(root: Path) -> dict:
    path = Path(root) / MARKER
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def history_complete(root: Path, key: str) -> bool:
    return _marks(root).get(key) == "complete"


def _mark(root: Path, key: str) -> None:
    marks = {**_marks(root), key: "complete"}
    path = Path(root) / MARKER
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(marks, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def backfill_history(store: SeriesStore, key: str, fetch, *, root: Path, earliest: date = date(1999, 1, 1)) -> int:
    """fetch(start, end) -> [(datetime, close)]. Returns how many closes were added. A failing window raises and leaves the series
    unfinished, so the next run continues from where it stopped."""
    if history_complete(root, key):
        return 0
    added = 0
    for _ in range(MAX_WINDOWS):
        points = store.read(key)
        if not points:
            return added  # nothing to anchor on yet; the normal refresh fills the recent years first
        oldest = points[0][0].date()
        if oldest <= earliest:
            break
        older = [p for p in fetch(earliest, oldest - timedelta(days=1)) if p[0].date() < oldest]
        if not older:
            break
        priced = [p for p in older if float(p[1]) > 0]  # the source sometimes returns 0 for very old sessions
        if not priced:
            break
        store.upsert(key, priced)
        added += len(priced)
    _mark(root, key)
    return added
