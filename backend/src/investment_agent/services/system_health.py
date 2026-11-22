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
from investment_agent.operations.backup import BackupError
from investment_agent.operations.restore import BackupCorrupt, personal_drill, read_personal_export, restore_local
from investment_agent.repositories.personal import RepositoryUnavailable

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
           {"id": "fundamentals", "label": "Báo cáo cơ bản (VNDirect)", "dir": "fundamentals", "max_days": 4},
           # refreshed once a ticker is 7 days old (market.statements), so 4 days read a healthy source as stale: 7 + 2 (owner, 21/11/2026)
           {"id": "statements", "label": "Báo cáo VNDirect", "dir": "statements", "max_days": 9},
           {"id": "financial-ratios", "label": "Chỉ số ngành", "dir": "financial-ratios", "max_days": 4},
           {"id": "valuation-check", "label": "Đối chiếu định giá (VNDirect)", "dir": "valuation-check", "max_days": 4},
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


BRIEF_DUE = (16, 30)  # by then the 15:30 run has normally sent the session's brief (it takes about 15 minutes)
_VN = timezone(timedelta(hours=7))


def brief_problem(lines: list[str], calendar, *, now: datetime) -> dict | None:
    """The latest session whose brief is due (from 16:30 that day) and was not published: either the run did not reach the step
    that sends it, or the step found data missing. Read from the after-close summary lines of the log."""
    local = now.astimezone(_VN)
    day = local.date()
    if not (calendar.is_session(day) and (local.hour, local.minute) >= BRIEF_DUE):
        earlier = calendar.sessions(day - timedelta(days=14), day - timedelta(days=1))
        if not earlier:
            return None
        day = earlier[-1]
    states = []
    for line in lines:
        bare = _BARE.match(line.lstrip("\ufeff"))
        if not bare or f'"session": "{day.isoformat()}"' not in line:
            continue
        try:
            summary = json.loads(line[line.index("{"):])
        except ValueError:
            continue
        if "published" in (summary.get("reports") or []) or summary.get("reason") == "already_published":
            return None
        states.append(summary)
    when = day.strftime("%d/%m/%Y")
    if any("incomplete" in (s.get("reports") or []) for s in states):
        detail = f"phiên {when} thiếu dữ liệu nên chưa gửi bản tin"
    else:
        detail = f"phiên {when}: lượt sau phiên chưa chạy tới bước gửi bản tin"
    return {"id": f"brief:{day.isoformat()}", "label": "Bản tin sau phiên", "detail": detail}


INDEX_SERIES = ("VNINDEX", "VN30")
INDEX_FLOOR = 100  # neither index has closed below 100 points; a lower stored close is in another unit (thousand points before 10/2022)


def index_unit_problems(data_dir: Path) -> list[dict]:
    """An index series holding closes below 100 points: ratios across it are wrong until it is rebuilt (cli index-closes-rebuild)."""
    out = []
    store = SeriesStore(Path(data_dir) / "trend-sources")
    for index in INDEX_SERIES:
        low = [t for t, v in store.points(f"{index}-1d") if float(v) < INDEX_FLOOR]
        if low:
            out.append({"id": f"index_units:{index}", "label": f"Lịch sử {index}",
                        "detail": f"{len(low)} phiên (đến {low[-1][8:10]}/{low[-1][5:7]}/{low[-1][:4]}) lưu theo nghìn điểm: chạy index-closes-rebuild"})
    return out


def vn100_problem(data_dir: Path) -> dict | None:
    from investment_agent.market.watchlist import load_watchlist, vn100_review
    review = vn100_review(load_watchlist(data_dir))
    if review is None:
        return None
    dmy = lambda iso: f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"  # noqa: E731
    return {"id": "vn100_review", "label": "Danh sách VN100",
            "detail": f"VN30 đổi thành phần ngày {dmy(review['vn30_changed_on'])} (HOSE xét lại rổ); danh sách VN100 lưu ngày "
                      f"{dmy(review['vn100_as_of'])} có thể đã cũ: cập nhật từ thông báo của HOSE"}


def calendar_problems(config_dir: Path, *, now: datetime) -> list[dict]:
    """HOSE's trading calendar of this year, and of next year from 1 December: without it prices, the brief and the session checks stop
    on 1 January. HOSE publishes the next year's calendar late in December; the file is made from that notice, never guessed."""
    from zoneinfo import ZoneInfo
    today = now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    out = []
    for year in (today.year, today.year + 1) if today.month == 12 else (today.year,):
        name = f"trading-calendar-hose-{year}.json"
        if (Path(config_dir) / name).is_file():
            continue
        when = "giá, bản tin và kiểm tra phiên đang dừng" if year == today.year else             f"từ 01/01/{year} giá, bản tin và kiểm tra phiên dừng; HOSE thường công bố cuối tháng 12"
        out.append({"id": f"calendar:{year}", "label": f"Lịch giao dịch HOSE {year}",
                    "detail": f"chưa có lịch giao dịch HOSE năm {year} (config/{name}): {when}"})
    return out


def gap_text(gap: dict) -> str:
    month, base = (f"{g[5:7]}/{g[:4]}" for g in (gap["month"], gap["base"]))
    return f"tháng {month} chưa tính được so cùng kỳ vì nguồn để trống số tháng {base} (không tự lấp)"


CPI_IDS = ("us_cpi_yoy", "us_core_cpi_yoy")  # their next month has a BLS date in Lịch vĩ mô Mỹ


def _explained(r: dict, gap: dict | None) -> bool:
    """The age comes only from the blank year-ago month: the newest figure is the month just before the one the source left blank."""
    if not gap:
        return False
    y, m = int(gap["month"][:4]), int(gap["month"][5:7])
    before = (y, m - 1) if m > 1 else (y - 1, 12)
    return (int(r["date"][:4]), int(r["date"][5:7])) == before


def _bls_date(data_dir: Path, year: int, month: int) -> str | None:
    """BLS's own date for the CPI of that month, from the stored Lịch vĩ mô Mỹ; None when the calendar does not list it."""
    import calendar as _cal
    path = Path(data_dir) / "macro" / "us-calendar.json"
    try:
        events = json.loads(path.read_text(encoding="utf-8")).get("events", []) if path.is_file() else []
    except (OSError, ValueError, AttributeError):  # damaged or another shape: no BLS date, the report still comes
        return None
    want = f"{_cal.month_name[month]} {year}"
    on = next((e["et"][:10] for e in events if e.get("kind") == "cpi" and e.get("detail") == want), None)
    return f"{on[8:10]}/{on[5:7]}/{on[:4]}" if on else None


def macro_problems(data_dir: Path, *, today) -> tuple[list[dict], list[dict]]:
    """Each automatic Vĩ mô indicator whose latest figure is past its own age (owner, 21/11/2026): the folder can be fresh while one
    series is months old. One problem per series, so each is announced once and its recovery too. A series with no figure yet (just
    added) and those entered by hand (reminded on their own) are left out.

    Kaizen (owner, 22/11/2026): when the age comes only from the year-ago month the source left blank, there is nothing to do; it is
    known, not a problem (not in Cần để ý, not sent), one line for the series sharing that month, until the next month is itself past
    the age (the blank month's date plus max_age_days); then it is a problem again."""
    from datetime import date
    from investment_agent.market.leading import MacroStore, load_indicators, macro_rows
    out, held, indicators = [], {}, load_indicators()
    limits = {i["id"]: i["max_age_days"] for i in indicators}
    sessions = {i["id"]: i.get("max_age_sessions") for i in indicators}
    for r in macro_rows(indicators, MacroStore(Path(data_dir)), today=today):
        if not (r["auto"] and r["stale"]):
            continue
        day, limit, gap = date.fromisoformat(r["date"]), limits[r["id"]], r.get("gap")
        if _explained(r, gap):
            until = date(int(gap["month"][:4]), int(gap["month"][5:7]), 1) + timedelta(days=limit)
            if today <= until:
                held.setdefault(gap["month"], []).append((r, gap, until))
                continue
        if r.get("age_sessions") is not None:  # a session indicator: old by HOSE sessions missed (owner, 22/11/2026)
            detail = f"số mới nhất ngày {day:%d/%m/%Y}, đã {r['age_sessions']} phiên HOSE chưa có số mới (hạn {sessions[r['id']]} phiên)"
        else:
            detail = f"số mới nhất ngày {day:%d/%m/%Y}, quá hạn {limit} ngày"
        if gap:  # the source left the year-ago month blank: said, never filled in
            detail += f"; {gap_text(gap)}"
        out.append({"id": f"macro:{r['id']}", "label": r["label"], "detail": detail})
    known = []
    for month, rows in held.items():
        gap, until = rows[0][1], max(u for _, _, u in rows)
        y, m = int(month[:4]), int(month[5:7])
        ny, nm = (y, m + 1) if m < 12 else (y + 1, 1)
        bls = _bls_date(data_dir, ny, nm) if all(r["id"] in CPI_IDS for r, _, _ in rows) else None
        known.append({"id": f"gap:{month}", "ids": [f"macro:{r['id']}" for r, _, _ in rows], "label": "; ".join(r["label"] for r, _, _ in rows),
                      "detail": f"{gap_text(gap)}. Không cần làm gì: tự hết khi có số tháng {nm:02d}/{ny}{f' (BLS hẹn công bố {bls})' if bls else ''}; "
                                f"đến {until:%d/%m/%Y} vẫn chưa có thì báo lại thành sự cố."})
    return out, known


def health_report(data_dir: Path, *, now: datetime, calendar=None, config_dir: Path | None = None) -> dict:
    from investment_agent.domain.pinned import CONFIG_DIR
    data_dir = Path(data_dir)
    root = data_dir.parent
    problems, sources = [], []
    problems.extend(calendar_problems(CONFIG_DIR if config_dir is None else config_dir, now=now))
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
    macro, known = macro_problems(data_dir, today=now.astimezone(timezone(timedelta(hours=7))).date())
    problems.extend(macro)
    lines = _read_tail(root / "logs" / "scheduler.log")
    steps = parse_log(lines or [])
    finishes = [l.lstrip("﻿").split(" ", 1)[0] for l in (lines or []) if " finish exit=" in l]
    last_finish = _when(finishes[-1]) if finishes else None
    if last_finish is None:
        problems.append({"id": "after-close", "label": "Lịch sau phiên", "detail": "chưa thấy lượt chạy nào trong nhật ký"})
    elif now - last_finish > timedelta(days=AFTER_CLOSE_MAX_DAYS):
        problems.append({"id": "after-close", "label": "Lịch sau phiên", "detail": f"lượt chạy xong gần nhất là {_dmy(last_finish)}"})
    problems.extend(index_unit_problems(data_dir))
    if vn100 := vn100_problem(data_dir):
        problems.append(vn100)
    if calendar is not None and lines is not None:
        brief = brief_problem(lines, calendar, now=now)
        if brief:
            problems.append(brief)
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
    return {"checked_at": now.isoformat(), "ok": not problems, "problems": problems, "sources": sources, "steps": steps, "last_finish": finishes[-1] if finishes else None, "drill": drill,
            "known": known}


def _read_drill(data_dir: Path) -> dict | None:
    path = data_dir.joinpath(*DRILL_FILE)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def alert_changes(problems: list[dict], data_dir: Path, *, save: bool, known: list[dict] | None = None) -> tuple[list[dict], list[str]]:
    """Problems not yet announced, and those announced that are over; with save, remembers the current set (after a delivered message).
    known: an announced problem now known (a blank year-ago month) is not over yet, so it is neither said to recover nor forgotten; one
    that was never announced is not sent."""
    path = Path(data_dir).joinpath(*STATE_FILE)
    saved = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    # a plain list is the announced set (before 22/11/2026); "held": announced problems now known, kept apart so one past its date is
    # announced again (owner review 22/11/2026) while one whose figure came back is said recovered once
    announced, was_held = (set(saved), set()) if isinstance(saved, list) else (set(saved["announced"]), set(saved["held"]))
    held = {i for k in known or [] for i in k["ids"]} & (announced | was_held)
    current = {p["id"] for p in problems}
    if save:
        _write(path, {"announced": sorted(current), "held": sorted(held)})
    return [p for p in problems if p["id"] not in announced], sorted((announced | was_held) - current - held)


def render_changes(new: list[dict], recovered: list[str]) -> str:
    lines = ["Tình trạng hệ thống"]
    lines += [f"⚠ {p['label']}: {p['detail']}" for p in new]
    if recovered:
        lines.append(f"Đã hồi phục: {', '.join(recovered)}")
    lines.append("Xem chi tiết ở Cài đặt.")
    return "\n".join(lines)


def backup_drill(backup_root: Path, data_dir: Path, *, now: datetime, repo=None, owner=None, force: bool = False) -> dict:
    """Restore the newest backup into a temporary folder, then remove it, once a week; with a repository, also its personal records into memory, compared
    with the live store (operations.restore.personal_drill). Only counts and the error type are kept. Firestore out of reach says nothing about the backup."""
    last = _read_drill(Path(data_dir))
    if not force and last and now - _when(last["at"]) < timedelta(days=DRILL_EVERY_DAYS):
        return {"status": "not_due"}
    backups = sorted(p for p in Path(backup_root).iterdir() if (p / "manifest.json").is_file()) if Path(backup_root).is_dir() else []
    if not backups:
        return {"status": "no_backup"}
    newest = backups[-1]
    out = {"status": "done", "at": now.isoformat(), "backup": newest.name, "ok": True, "files": 0, "error": None}
    try:
        with tempfile.TemporaryDirectory(prefix="investment-drill-") as tmp:
            out["files"] = len(restore_local(newest, Path(tmp) / "restored"))
        read_personal_export(newest)
        if repo is not None:
            out["personal"] = personal_drill(newest, repo, owner)
            if not out["personal"]["ok"]:
                out.update(ok=False, error="PersonalMismatch")
    except RepositoryUnavailable:
        out["personal"] = "unavailable"
    except (BackupError, OSError, ValueError, KeyError) as exc:
        out.update(ok=False, error=type(exc).__name__)
    _write(Path(data_dir).joinpath(*DRILL_FILE), out)
    return out
