import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from investment_agent.market.series import SeriesStore
from investment_agent.services.system_health import SOURCES, alert_changes, backup_drill, health_report, parse_log, render_changes

NOW = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)


def stamp(hours_ago):
    return (NOW - timedelta(hours=hours_ago)).isoformat()


def healthy(tmp_path):
    data = tmp_path / "data"
    for s in SOURCES:
        if s["dir"]:
            (data / s["dir"]).mkdir(parents=True, exist_ok=True)
            f = data / s["dir"] / "x.json"
            f.write_text("{}", encoding="utf-8")
            os.utime(f, (NOW.timestamp() - 3600, NOW.timestamp() - 3600))
    SeriesStore(data / "trend-sources").upsert("VNINDEX-1d", [(NOW.replace(tzinfo=None) - timedelta(days=1), "1700")])
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "scheduler.log").write_text(f"﻿{stamp(2)} market-sync exit=0 {{}}\n{stamp(2)} finish exit=0 pid=1\n", encoding="utf-8")
    backup = tmp_path / "backups" / "20261109T010000Z-daily"
    backup.mkdir(parents=True)
    return data


def report(data):
    return health_report(data, now=NOW)


def drilled(data, hours_ago=1, ok=True):
    (data / "alerts").mkdir(exist_ok=True)
    (data / "alerts" / "restore-drill.json").write_text(json.dumps({"at": stamp(hours_ago), "ok": ok, "backup": "b", "files": 3, "error": None if ok else "BackupCorrupt"}), encoding="utf-8")


def test_a_step_is_read_with_its_name_exit_and_how_many_times_in_a_row_it_has_failed_and_nothing_else():
    steps = parse_log([f"{stamp(9)} macro-sync exit=1 {{\"secret\": \"HPG\"}}", f"{stamp(8)} macro-sync exit=1 x", f"{stamp(7)} market-sync VNINDEX exit=0 x",
                       f"{stamp(6)} exit=2 {{}}", f"{stamp(5)} start pid=3", f"{stamp(4)} macro-sync exit=0 x", f"{stamp(3)} macro-sync exit=1 x", f"{stamp(1)} finish exit=0 pid=1"])
    by = {s["step"]: s for s in steps}
    assert by["macro-sync"]["failing"] == 1 and by["macro-sync"]["exit"] == 1 and by["market-sync VNINDEX"]["failing"] == 0
    assert by["scheduled-run"]["exit"] == 2 and "finish" not in by and set(by["macro-sync"]) == {"step", "last_at", "exit", "failing"}  # no payloads


def test_nothing_wrong_when_steps_pass_sources_are_fresh_and_the_restore_drill_is_recent(tmp_path):
    data = healthy(tmp_path)
    drilled(data)
    out = report(data)
    assert out["problems"] == [] and out["ok"] is True and out["sources"][0]["stale"] is False


def test_a_step_failing_twice_running_is_a_problem_once_is_not(tmp_path):
    data = healthy(tmp_path)
    drilled(data)
    log = tmp_path / "logs" / "scheduler.log"
    base = log.read_text(encoding="utf-8")
    log.write_text(base + f"{stamp(1)} macro-sync exit=1 x\n", encoding="utf-8")
    assert report(data)["problems"] == []
    log.write_text(base + f"{stamp(1)} macro-sync exit=1 x\n{stamp(0)} macro-sync exit=1 x\n", encoding="utf-8")
    assert [p["id"] for p in report(data)["problems"]] == ["step:macro-sync"]


def test_old_data_is_a_problem_even_though_every_step_said_it_passed(tmp_path):
    data = healthy(tmp_path)
    drilled(data)
    f = data / "bank-notes" / "x.json"
    os.utime(f, (NOW.timestamp() - 20 * 86400, NOW.timestamp() - 20 * 86400))
    SeriesStore(data / "trend-sources").upsert("VNINDEX-1d", [])
    out = report(data)
    assert "source:bank-notes" in [p["id"] for p in out["problems"]]


def test_prices_go_stale_by_their_last_session_and_a_dead_after_close_run_is_seen(tmp_path):
    data = healthy(tmp_path)
    drilled(data)
    assert report(data)["problems"] == []
    later = NOW + timedelta(days=8)
    ids = [p["id"] for p in health_report(data, now=later)["problems"]]
    assert "source:prices" in ids and "after-close" in ids


def test_a_missing_log_or_a_failed_or_old_drill_is_said(tmp_path):
    data = healthy(tmp_path)
    drilled(data, ok=False)
    assert "drill" in [p["id"] for p in report(data)["problems"]]
    drilled(data, hours_ago=24 * 20)
    assert "drill" in [p["id"] for p in report(data)["problems"]]
    drilled(data)
    (tmp_path / "logs" / "scheduler.log").unlink()
    assert "after-close" in [p["id"] for p in report(data)["problems"]]


def test_each_problem_is_announced_once_and_its_recovery_too(tmp_path):
    problems = [{"id": "step:a", "label": "a", "detail": "lỗi"}]
    new, back = alert_changes(problems, tmp_path, save=False)
    assert [p["id"] for p in new] == ["step:a"] and back == []
    assert "lỗi" in render_changes(new, back)
    alert_changes(problems, tmp_path, save=True)
    assert alert_changes(problems, tmp_path, save=False) == ([], [])
    new, back = alert_changes([], tmp_path, save=False)
    assert new == [] and back == ["step:a"]
    assert "hồi phục" in render_changes(new, back).lower()


def _backup(root: Path, name="20261109T010000Z-daily"):
    from investment_agent.operations.backup import create_backup
    data = root.parent / "src"
    (data / "macro").mkdir(parents=True, exist_ok=True)
    (data / "macro" / "wti.json").write_text("{}", encoding="utf-8")  # backups copy an allowlist of folders only
    return create_backup(data, root, personal_export={"records": [1]}, now=NOW, kind="daily")


def test_the_drill_restores_the_newest_backup_into_a_temporary_folder_and_says_a_corrupt_one(tmp_path):
    root = tmp_path / "backups"
    made = _backup(root)
    data = tmp_path / "data"
    data.mkdir()
    out = backup_drill(root, data, now=NOW)
    assert out["ok"] is True and out["backup"] == made.path.name and out["files"] >= 1
    assert json.loads((data / "alerts" / "restore-drill.json").read_text(encoding="utf-8"))["ok"] is True
    assert backup_drill(root, data, now=NOW + timedelta(days=1))["status"] == "not_due"
    victim = next(p for p in made.path.rglob("*.json") if p.name == "wti.json")
    victim.write_text('{"x":1}', encoding="utf-8")
    out = backup_drill(root, data, now=NOW + timedelta(days=8))
    assert out["ok"] is False and out["error"] == "BackupCorrupt"


# --- Bản tin sau phiên: from 16:30 of a session day, that session's brief must have gone out ---

def _cal():
    from datetime import date
    from investment_agent.market.calendar import TradingCalendar
    return TradingCalendar(version="t", source="test", holidays=frozenset(), first=date(2026, 1, 1), last=date(2026, 12, 31))


def _log(data, *lines):
    path = data.parent / "logs" / "scheduler.log"
    path.write_text(path.read_text(encoding="utf-8") + "".join(f"{line}\n" for line in lines), encoding="utf-8")


def test_a_brief_not_published_by_half_past_four_is_a_problem_and_a_published_one_is_not(tmp_path):
    data = healthy(tmp_path)
    drilled(data)
    at = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)  # 17:00 in Vietnam, Friday
    problems = {p["id"]: p for p in health_report(data, now=at, calendar=_cal())["problems"]}
    assert problems["brief:2026-11-13"]["label"] == "Bản tin sau phiên" and "chưa chạy tới bước gửi" in problems["brief:2026-11-13"]["detail"]
    _log(data, '2026-11-13T15:40:00+07:00 exit=0 {"status": "ok", "run": true, "session": "2026-11-13", "reports": ["incomplete"], "delivered": 0}')
    assert "thiếu dữ liệu" in {p["id"]: p for p in health_report(data, now=at, calendar=_cal())["problems"]}["brief:2026-11-13"]["detail"]
    _log(data, '2026-11-13T20:05:00+07:00 exit=0 {"status": "ok", "run": true, "session": "2026-11-13", "reports": ["published"], "delivered": 1}')
    assert not any(p["id"].startswith("brief:") for p in health_report(data, now=at, calendar=_cal())["problems"])


def test_before_half_past_four_the_previous_session_is_the_one_checked(tmp_path):
    data = healthy(tmp_path)
    drilled(data)
    _log(data, '2026-11-12T15:40:00+07:00 exit=0 {"status": "ok", "run": false, "reason": "already_published", "session": "2026-11-12"}')
    at = datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc)  # 15:00 in Vietnam
    assert not any(p["id"].startswith("brief:") for p in health_report(data, now=at, calendar=_cal())["problems"])
    assert not any(p["id"].startswith("brief:") for p in health_report(data, now=at)["problems"])  # no calendar given: not checked
