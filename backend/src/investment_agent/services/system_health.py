"""Tình trạng hệ thống: whether the unattended work is really happening. A step that fails twice running, data older than it should be
even though every step said it passed, an after-close run that stopped happening, and a backup that does not restore are problems; each
is announced once, and again when it recovers. Reads only step names and exit codes from the log, never what a step printed."""

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from investment_agent.market.series import SeriesStore
from investment_agent.operations.restore import BackupCorrupt, restore_local

LOG_LINES = 4000
FAILS_BEFORE_ALERT = 2
AFTER_CLOSE_MAX_DAYS = 2
DRILL_EVERY_DAYS, DRILL_MAX_DAYS = 7, 14
DRILL_FILE = ("alerts", "restore-drill.json")
STATE_FILE = ("alerts", "system-health.json")
# "dir": a folder whose newest file shows when the source last wrote; None for prices, judged by their last session.
SOURCES = ({"id": "prices", "label": "Giá VN-Index", "dir": None, "max_days": 6},
           {"id": "macro", "label": "Vĩ mô", "dir": "macro", "max_days": 3},
           {"id": "trend", "label": "Xu hướng", "dir": "trend", "max_days": 6},
           {"id": "events", "label": "Lịch sự kiện", "dir": "events", "max_days": 3},
           {"id": "fundamentals", "label": "Báo cáo Vnstock", "dir": "fundamentals", "max_days": 4},
           {"id": "statements", "label": "Báo cáo VNDirect", "dir": "statements", "max_days": 4},
           {"id": "financial-ratios", "label": "Chỉ số ngành", "dir": "financial-ratios", "max_days": 4},
           {"id": "bank-notes", "label": "Thuyết minh ngân hàng (Vietcap)", "dir": "bank-notes", "max_days": 10})
_NAMED = re.compile(r"^(\S+) (.+?) exit=(\d+)(?:\s|$)")
_BARE = re.compile(r"^(\S+) exit=(\d+)(?:\s|$)")
_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T")


def parse_log(lines: list[str]) -> list[dict]:
    """One row per step, oldest line first in: last run, last exit code, and how many runs in a row have failed. "finish" is left out."""
    steps: dict[str, dict] = {}
    for line in lines:
        line = line.lstrip("﻿")
        if not _STAMP.match(line):
            continue
        bare, named = _BARE.match(line), _NAMED.match(line)
        at, name, code = (bare[1], "scheduled-run", int(bare[2])) if bare else (named[1], named[2], int(named[3])) if named else (None, None, 0)
        if name is None or name == "finish":
            continue
        old = steps.get(name, {"failing": 0})
        steps[name] = {"step": name, "last_at": at, "exit": code, "failing": old["failing"] + 1 if code else 0}
    return [steps[k] for k in sorted(steps)]


def _when(text: str) -> datetime:
    return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", text))


def _newest(folder: Path) -> datetime | None:
    times = [p.stat().st_mtime for p in folder.iterdir() if p.is_file()] if folder.is_dir() else []
    return datetime.fromtimestamp(max(times), timezone.utc) if times else None


def _read_tail(path: Path) -> list[str] | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-LOG_LINES:]


def _dmy(d: datetime) -> str:
    return d.strftime("%d/%m/%Y")


def health_report(data_dir: Path, *, now: datetime) -> dict:
    data_dir = Path(data_dir)
    root = data_dir.parent
    problems, sources = [], []
    for s in SOURCES:
        if s["dir"] is None:
            points = SeriesStore(data_dir / "trend-sources").read("VNINDEX-1d")
            last = points[-1][0].replace(tzinfo=timezone.utc) if points else None
        else:
            last = _newest(data_dir / s["dir"])
        stale = last is None or now - last > timedelta(days=s["max_days"])
        sources.append({"id": s["id"], "label": s["label"], "last": None if last is None else last.isoformat(), "max_days": s["max_days"], "stale": stale})
        if stale:
            problems.append({"id": f"source:{s['id']}", "label": s["label"],
                             "detail": "chưa có dữ liệu" if last is None else f"cập nhật lần cuối {_dmy(last)}, quá {s['max_days']} ngày"})
    lines = _read_tail(root / "logs" / "scheduler.log")
    steps = parse_log(lines or [])
    finishes = [l.lstrip("﻿").split(" ", 1)[0] for l in (lines or []) if " finish exit=" in l]
    last_finish = _when(finishes[-1]) if finishes else None
    if last_finish is None:
        problems.append({"id": "after-close", "label": "Lịch sau phiên", "detail": "chưa thấy lượt chạy nào trong nhật ký"})
    elif now - last_finish > timedelta(days=AFTER_CLOSE_MAX_DAYS):
        problems.append({"id": "after-close", "label": "Lịch sau phiên", "detail": f"lượt chạy xong gần nhất là {_dmy(last_finish)}"})
    for s in steps:
        if s["failing"] >= FAILS_BEFORE_ALERT:
            problems.append({"id": f"step:{s['step']}", "label": s["step"], "detail": f"lỗi {s['failing']} lần liên tiếp (mã {s['exit']})"})
    drill = _read_drill(data_dir)
    if drill is None:
        problems.append({"id": "drill", "label": "Diễn tập khôi phục", "detail": "chưa diễn tập lần nào"})
    elif not drill["ok"]:
        problems.append({"id": "drill", "label": "Diễn tập khôi phục", "detail": f"bản sao lưu {drill['backup']} không khôi phục được ({drill['error']})"})
    elif now - _when(drill["at"]) > timedelta(days=DRILL_MAX_DAYS):
        problems.append({"id": "drill", "label": "Diễn tập khôi phục", "detail": f"lần gần nhất {_dmy(_when(drill['at']))}"})
    return {"checked_at": now.isoformat(), "ok": not problems, "problems": problems, "sources": sources, "steps": steps, "last_finish": finishes[-1] if finishes else None, "drill": drill}


def _read_drill(data_dir: Path) -> dict | None:
    path = data_dir.joinpath(*DRILL_FILE)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def alert_changes(problems: list[dict], data_dir: Path, *, save: bool) -> tuple[list[dict], list[str]]:
    """Problems not yet announced, and those announced that are over; with save, remembers the current set (after a delivered message)."""
    path = Path(data_dir).joinpath(*STATE_FILE)
    known = set(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else set()
    current = {p["id"] for p in problems}
    if save:
        _write(path, sorted(current))
    return [p for p in problems if p["id"] not in known], sorted(known - current)


def render_changes(new: list[dict], recovered: list[str]) -> str:
    lines = ["Tình trạng hệ thống"]
    lines += [f"⚠ {p['label']}: {p['detail']}" for p in new]
    if recovered:
        lines.append(f"Đã hồi phục: {', '.join(recovered)}")
    lines.append("Xem chi tiết ở Cài đặt.")
    return "\n".join(lines)


def backup_drill(backup_root: Path, data_dir: Path, *, now: datetime) -> dict:
    """Restore the newest backup into a temporary folder, then remove it, once a week. Only counts and the error type are kept."""
    last = _read_drill(Path(data_dir))
    if last and now - _when(last["at"]) < timedelta(days=DRILL_EVERY_DAYS):
        return {"status": "not_due"}
    backups = sorted(p for p in Path(backup_root).iterdir() if (p / "manifest.json").is_file()) if Path(backup_root).is_dir() else []
    if not backups:
        return {"status": "no_backup"}
    newest = backups[-1]
    out = {"status": "done", "at": now.isoformat(), "backup": newest.name, "ok": True, "files": 0, "error": None}
    try:
        with tempfile.TemporaryDirectory(prefix="investment-drill-") as tmp:
            out["files"] = len(restore_local(newest, Path(tmp) / "restored"))
        json.loads((newest / "personal-export.json").read_text(encoding="utf-8"))
    except (BackupCorrupt, OSError, ValueError, KeyError) as exc:
        out.update(ok=False, error=type(exc).__name__)
    _write(Path(data_dir).joinpath(*DRILL_FILE), out)
    return out
