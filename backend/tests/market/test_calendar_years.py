"""Lịch giao dịch qua mốc đổi năm (owner, 23/11/2026; docs/superpowers/specs/2026-11-23-lich-qua-nam-design.md). Made-up calendars with a source."""

import json
from datetime import date

import pytest

from investment_agent.cli import CalendarMissing, load_calendar
from investment_agent.jobs.schedule import _next_session, _previous_session


def write(folder, year, holidays, first=None, last=None):
    path = folder / f"trading-calendar-hose-{year}.json"
    path.write_text(json.dumps({"version": f"hose-{year}.1", "source": f"HOSE thông báo mẫu {year}", "first": first or f"{year}-01-01",
                                "last": last or f"{year}-12-31", "holidays": holidays}), encoding="utf-8")
    return path


def test_adjacent_years_are_read_as_one_so_a_look_back_crosses_new_year(tmp_path):
    write(tmp_path, 2026, ["2026-01-01", "2026-12-31"])
    p27 = write(tmp_path, 2027, ["2027-01-01"])
    cal = load_calendar(p27)
    assert (cal.first, cal.last) == (date(2026, 1, 1), date(2027, 12, 31))
    assert _previous_session(cal, date(2027, 1, 4)) == date(2026, 12, 30)  # 31/12 and 01/01 closed, then the weekend
    assert cal.sessions(date(2026, 12, 28), date(2027, 1, 8)) == (date(2026, 12, 28), date(2026, 12, 29), date(2026, 12, 30), date(2027, 1, 4),
                                                                 date(2027, 1, 5), date(2027, 1, 6), date(2027, 1, 7), date(2027, 1, 8))
    assert "hose-2026.1" in cal.version and "hose-2027.1" in cal.version and "mẫu 2026" in cal.source and "mẫu 2027" in cal.source
    cal26 = load_calendar(tmp_path / "trading-calendar-hose-2026.json")  # the year before reaches the next too
    assert _next_session(cal26, date(2026, 12, 30)) == date(2027, 1, 4)


def test_the_scheduler_catches_up_the_last_session_of_last_year_and_counts_what_it_missed_across_new_year(tmp_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from investment_agent.jobs.schedule import ReportState, decide
    write(tmp_path, 2026, ["2026-12-31"])
    cal = load_calendar(write(tmp_path, 2027, ["2027-01-01"]))
    vn = ZoneInfo("Asia/Ho_Chi_Minh")
    morning = decide(datetime(2027, 1, 4, 8, 30, tzinfo=vn), cal, ReportState(published=frozenset({date(2026, 12, 29)}), attempts={}))
    assert (morning.run, morning.reason, morning.session_date) == (True, "catch_up", date(2026, 12, 30))  # not "no_session"
    evening = decide(datetime(2027, 1, 5, 20, 0, tzinfo=vn), cal, ReportState(published=frozenset({date(2026, 12, 29)}), attempts={}))
    assert (evening.session_date, evening.missed_sessions) == (date(2027, 1, 5), 2)  # 30/12 and 04/01, not a range error
    assert "weekly" in decide(datetime(2026, 12, 30, 20, 0, tzinfo=vn), cal, ReportState(published=frozenset(), attempts={})).kinds


def test_the_brief_check_of_system_health_looks_back_across_new_year(tmp_path):
    from datetime import datetime, timezone

    from investment_agent.services.system_health import brief_problem
    write(tmp_path, 2026, [])
    cal = load_calendar(write(tmp_path, 2027, ["2027-01-01"]))
    brief_problem([], cal, now=datetime(2027, 1, 4, 1, 0, tzinfo=timezone.utc))  # 08:00 Hà Nội: looks back 14 days into 2026, no range error


def test_a_year_alone_is_its_own_range_and_years_that_do_not_meet_are_not_joined(tmp_path):
    p26 = write(tmp_path, 2026, [])
    assert (load_calendar(p26).first, load_calendar(p26).last) == (date(2026, 1, 1), date(2026, 12, 31))
    write(tmp_path, 2027, [], first="2027-01-05")  # a gap of four days: not joined, never taken as sessions
    cal = load_calendar(p26)
    assert cal.last == date(2026, 12, 31)
    with pytest.raises(ValueError):
        cal.is_session(date(2027, 1, 4))


def test_a_broken_file_for_the_year_next_door_leaves_this_years_calendar_standing(tmp_path):
    """Review 23/11/2026: a 2027 file written with a trailing comma, or without "last", must not stop the 2026 calendar."""
    p26 = write(tmp_path, 2026, ["2026-01-01"])
    (tmp_path / "trading-calendar-hose-2027.json").write_text('{"version": "hose-2027.1", "source": "HOSE", "holidays": [],}', encoding="utf-8")
    assert load_calendar(p26).last == date(2026, 12, 31)
    (tmp_path / "trading-calendar-hose-2027.json").write_text(json.dumps({"version": "v", "source": "HOSE", "first": "2027-01-01", "holidays": []}),
                                                              encoding="utf-8")
    (tmp_path / "trading-calendar-hose-2025.json").write_text(json.dumps({"version": "v", "source": "synthetic", "first": "2025-01-01",
                                                                         "last": "2025-12-31", "holidays": []}), encoding="utf-8")
    assert (load_calendar(p26).first, load_calendar(p26).last) == (date(2026, 1, 1), date(2026, 12, 31))  # no "last"; no source


def test_the_owners_own_calendar_is_read_as_it_is(tmp_path):
    write(tmp_path, 2027, [])
    own = tmp_path / "trading-calendar.json"
    own.write_text(json.dumps({"version": "own.1", "source": "chủ sở hữu, từ thông báo HOSE", "first": "2026-01-01", "last": "2026-12-31",
                               "holidays": []}), encoding="utf-8")
    assert load_calendar(own).last == date(2026, 12, 31)


def test_the_scheduled_run_and_the_brief_put_the_missing_year_sentence_in_the_log(tmp_path, capsys):
    """Spec §2: the sentence reaches logs/scheduler.log, not only the exception's name (review 23/11/2026)."""
    from investment_agent.cli import brief_snapshot_cli, scheduled_run
    missing = tmp_path / "trading-calendar-hose-2027.json"
    for run in (lambda: scheduled_run(missing, tmp_path), lambda: brief_snapshot_cli(tmp_path, missing)):
        run()
        out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert out["reason"] == "CalendarMissing" and out["message"].startswith("chưa có lịch giao dịch HOSE 2027")


def test_the_weekly_brief_stops_on_a_missing_calendar_instead_of_counting_every_weekday(tmp_path, capsys):
    """Spec §2 (owner, 23/11/2026): no step counts every weekday as a session; the weekly brief did, so 01/01 was a session missing figures.
    It stops before reading anything personal or touching Telegram."""
    from datetime import datetime, timezone

    from investment_agent.cli import weekly_brief_cli
    saturday = datetime(2027, 1, 2, 3, 0, tzinfo=timezone.utc)
    assert weekly_brief_cli(tmp_path, tmp_path / "trading-calendar-hose-2027.json", now=saturday) == 2
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["status"] == "not_configured" and out["message"].startswith("chưa có lịch giao dịch HOSE 2027")


def test_a_missing_year_says_what_is_missing_and_what_to_do(tmp_path):
    write(tmp_path, 2026, [])
    with pytest.raises(CalendarMissing) as err:
        load_calendar(tmp_path / "trading-calendar-hose-2027.json")
    assert str(err.value) == ("chưa có lịch giao dịch HOSE 2027 (config/trading-calendar-hose-2027.json); tạo từ thông báo của HOSE")
    assert isinstance(err.value, FileNotFoundError)
