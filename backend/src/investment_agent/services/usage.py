"""Sử dụng phần mềm (owner, 21/11/2026): how often each page is opened and which requests took longer than a second, so the next
improvements go where the owner actually works. Kept on this computer only, in data/usage: visits per page and day (90 days) and the
last 200 slow requests. A slow request's path is masked (a ticker or an amount becomes "*"), so the files never name a holding or a sum.
Never sent anywhere."""

from __future__ import annotations

import json
import os
import re
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

KEEP_DAYS = 90
KEEP_SLOW = 200
SLOW_SECONDS = 1.0
WORD = re.compile(r"^[a-z][a-z-]{0,39}$")
_lock = threading.Lock()


def _dir(data_dir: Path) -> Path:
    return Path(data_dir) / "usage"


def _read(path: Path, empty):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else empty
    except (OSError, ValueError):
        return empty  # unreadable: start again rather than fail the page


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def page_key(pathname: str) -> str | None:
    """A web page by its first segment ("/research/HPG" is "/research"); None for anything that is not a plain page path."""
    if not isinstance(pathname, str) or not pathname.startswith("/"):
        return None
    first = pathname.split("?", 1)[0].split("#", 1)[0].strip("/").split("/", 1)[0]
    if first == "":
        return "/"
    return f"/{first}" if WORD.match(first) else None


def mask_path(path: str) -> str:
    """Words of the path kept; any other segment (a ticker, an amount, an id) becomes "*"."""
    return "/".join(s if (s == "" or WORD.match(s)) else "*" for s in path.split("?", 1)[0].split("/"))


def record_visit(data_dir: Path, page: str, *, today: date) -> None:
    path = _dir(data_dir) / "visits.json"
    with _lock:
        days = _read(path, {}).get("days", {})
        oldest = (today - timedelta(days=KEEP_DAYS - 1)).isoformat()
        days = {d: pages for d, pages in days.items() if d >= oldest}
        counts = days.setdefault(today.isoformat(), {})
        counts[page] = counts.get(page, 0) + 1
        _write(path, {"days": dict(sorted(days.items()))})


def record_slow(data_dir: Path, *, method: str, path: str, seconds: float, status: int, at: datetime) -> None:
    file = _dir(data_dir) / "slow.json"
    with _lock:
        rows = _read(file, [])
        rows.append({"at": at.isoformat(), "method": method, "path": mask_path(path), "seconds": round(seconds, 2), "status": status})
        _write(file, rows[-KEEP_SLOW:])


def usage_summary(data_dir: Path, *, today: date) -> dict:
    days = _read(_dir(data_dir) / "visits.json", {}).get("days", {})
    totals: dict[str, dict] = defaultdict(lambda: {"last_30": 0, "last_7": 0, "today": 0, "last_day": None})
    for day, pages in days.items():
        age = (today - date.fromisoformat(day)).days
        for page, n in pages.items():
            row = totals[page]
            if age < 30:
                row["last_30"] += n
            if age < 7:
                row["last_7"] += n
            if age == 0:
                row["today"] += n
            row["last_day"] = max(row["last_day"] or day, day)
    pages = sorted(({"page": p, **r} for p, r in totals.items() if r["last_30"]), key=lambda r: (-r["last_30"], r["page"]))
    groups: dict[str, dict] = {}
    for row in _read(_dir(data_dir) / "slow.json", []):
        key = f"{row['method']} {row['path']}"
        g = groups.setdefault(key, {"path": key, "count": 0, "worst": 0.0, "last": row["at"]})
        g["count"] += 1
        g["worst"] = max(g["worst"], row["seconds"])
        g["last"] = max(g["last"], row["at"])
    slow = sorted(groups.values(), key=lambda g: (-g["count"], -g["worst"]))
    return {"pages": pages, "slow": [{**g, "worst": f"{g['worst']:.2f}"} for g in slow], "slow_threshold": f"{SLOW_SECONDS:.1f}",
            "since": min(days) if days else None}
