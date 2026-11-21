"""scheduler.log moves to a file of its own each month (owner, 21/11/2026), keeping six months; the new file starts with the last lines
of the old one, so Tình trạng hệ thống still finds the last finished run and how many times in a row a step failed."""

from datetime import date

from investment_agent.jobs.log_rotate import rotate


def write(path, months_lines):
    path.write_text("﻿" + "".join(f"{m}-28T08:30:00+07:00 step{i} exit=0 {{}}\n" for m, n in months_lines for i in range(n)), encoding="utf-8")


def test_a_log_begun_last_month_is_kept_whole_under_its_month_and_the_new_one_carries_its_tail(tmp_path):
    log = tmp_path / "scheduler.log"
    write(log, [("2026-11", 300)])
    out = rotate(log, today=date(2026, 12, 1), carry=200)
    assert out == {"rotated": "scheduler-2026-11.log", "removed": []}
    assert (tmp_path / "scheduler-2026-11.log").read_text(encoding="utf-8-sig").count("\n") == 300
    kept = log.read_text(encoding="utf-8-sig").splitlines()
    assert len(kept) == 200 and kept[-1].startswith("2026-11-28T08:30:00+07:00 step299")


def test_a_log_of_this_month_is_left_alone(tmp_path):
    log = tmp_path / "scheduler.log"
    write(log, [("2026-12", 5)])
    assert rotate(log, today=date(2026, 12, 9)) == {"rotated": None, "removed": []}
    assert not list(tmp_path.glob("scheduler-*.log"))


def test_only_six_months_of_old_logs_are_kept(tmp_path):
    for month in ("2026-04", "2026-05", "2026-06", "2026-11"):
        (tmp_path / f"scheduler-{month}.log").write_text("x\n", encoding="utf-8")
    log = tmp_path / "scheduler.log"
    write(log, [("2026-11", 3)])
    out = rotate(log, today=date(2026, 12, 1))
    assert out["removed"] == ["scheduler-2026-04.log", "scheduler-2026-05.log"]  # December keeps June to November
    assert sorted(p.name for p in tmp_path.glob("scheduler-*.log")) == ["scheduler-2026-06.log", "scheduler-2026-11.log"]


def test_a_missing_or_empty_log_is_nothing_to_do(tmp_path):
    assert rotate(tmp_path / "scheduler.log", today=date(2026, 12, 1)) == {"rotated": None, "removed": []}
