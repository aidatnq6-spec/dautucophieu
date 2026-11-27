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
    (data / "index-history").mkdir(parents=True, exist_ok=True)  # lịch sử định giá: one ticker refreshed an hour ago
    fresh = data / "index-history" / "AAA.json"
    fresh.write_text("{}", encoding="utf-8")
    os.utime(fresh, (NOW.timestamp() - 3600, NOW.timestamp() - 3600))
    for folder in ("foreign", "proprietary"):  # kho theo phiên: a session of today with figures
        (data / folder).mkdir(parents=True, exist_ok=True)
        (data / folder / "2026-11-09.json").write_text(json.dumps({"date": "2026-11-09", "stocks": {}}), encoding="utf-8")
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


def test_each_automatic_indicator_past_its_age_is_named_as_its_own_problem(tmp_path):
    """Owner, 21/11/2026: the Vĩ mô folder can be fresh while one series is months old; each such series is said once, by name."""
    from datetime import date
    from investment_agent.market.leading import MacroStore
    data = healthy(tmp_path)
    drilled(data)
    store = MacroStore(data)
    store.upsert("us_cpi_yoy", [(date(2026, 8, 1), "2.9")], entry="auto")      # 100 days against 75
    store.upsert("vn_interbank_1w", [(date(2026, 11, 6), "4.5")], entry="auto")  # 3 days against 5: fine
    problems = {p["id"]: p for p in report(data)["problems"]}
    assert set(problems) == {"macro:us_cpi_yoy"}
    assert problems["macro:us_cpi_yoy"]["label"] == "Lạm phát CPI của Mỹ (so cùng kỳ)"
    assert problems["macro:us_cpi_yoy"]["detail"] == "số mới nhất ngày 01/08/2026, quá hạn 75 ngày"


def test_an_indicator_old_because_the_source_left_the_year_ago_month_blank_says_so(tmp_path):
    from datetime import date
    from investment_agent.market.leading import MacroStore
    data = healthy(tmp_path)
    drilled(data)
    store = MacroStore(data)
    store.upsert("us_cpi_yoy", [(date(2026, 8, 1), "2.9")], entry="auto")
    store.record_gaps({"us_cpi_yoy": {"month": "2026-10", "base": "2025-10"}})
    detail = next(p for p in report(data)["problems"] if p["id"] == "macro:us_cpi_yoy")["detail"]
    assert detail == ("số mới nhất ngày 01/08/2026, quá hạn 75 ngày; tháng 10/2026 chưa tính được so cùng kỳ vì nguồn để trống số "
                      "tháng 10/2025 (không tự lấp)")


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


def test_next_years_hose_calendar_missing_from_december_is_a_problem_and_this_years_missing_always_is(tmp_path):
    data, config = healthy(tmp_path), tmp_path / "config"
    config.mkdir()
    (config / "trading-calendar-hose-2026.json").write_text("{}", encoding="utf-8")
    ids = lambda now: {p["id"]: p for p in health_report(data, now=now, config_dir=config)["problems"]}  # noqa: E731
    assert "calendar:2027" not in ids(NOW)  # November: not yet
    december = datetime(2026, 11, 30, 18, 0, tzinfo=timezone.utc)  # 01/12 01:00 in Hà Nội
    assert ids(december)["calendar:2027"]["detail"] == ("chưa có lịch giao dịch HOSE năm 2027 (config/trading-calendar-hose-2027.json): "
                                                         "từ 01/01/2027 giá, bản tin và kiểm tra phiên dừng; HOSE thường công bố cuối tháng 12")
    (config / "trading-calendar-hose-2027.json").write_text("{}", encoding="utf-8")
    assert "calendar:2027" not in ids(december)
    (config / "trading-calendar-hose-2026.json").unlink()
    assert ids(december)["calendar:2026"]["detail"].startswith("chưa có lịch giao dịch HOSE năm 2026")


def test_statements_are_old_only_past_their_seven_day_refresh_and_two_days_more():
    """statements-sync refreshes a ticker once it is 7 days old, so 4 days said a healthy source was stale (owner, 21/11/2026)."""
    from investment_agent.market.statements import MAX_AGE_DAYS
    statements = next(s for s in SOURCES if s["id"] == "statements")
    assert statements["max_days"] == MAX_AGE_DAYS + 2 == 9
    assert {s["id"]: s["max_days"] for s in SOURCES}["financial-ratios"] == 4  # the others keep the spec's limits


def macro(out):
    """The Vĩ mô problems only: the fixture's other sources are fresh on NOW (9/11), not on the later days these tests look at."""
    return [p["id"] for p in out["problems"] if p["id"].startswith("macro:")]


def _cpi_gap(data, *, last):
    """Both US CPI series stop one month before October 2026, whose year-ago month the source left blank (as on 22/11/2026)."""
    from investment_agent.market.leading import MacroStore
    store = MacroStore(data)
    for key in ("us_cpi_yoy", "us_core_cpi_yoy"):
        store.upsert(key, [(last, "2.9")], entry="auto")
    store.record_gaps({k: {"month": "2026-10", "base": "2025-10"} for k in ("us_cpi_yoy", "us_core_cpi_yoy")})


def test_a_gap_that_alone_explains_the_age_is_known_once_not_a_problem_until_the_next_month_is_due(tmp_path):
    """Owner, 22/11/2026 (kaizen): the source has October but not October 2025, so nothing is to be done. One known line for both
    series, saying when it ends: BLS's date for November's CPI when the calendar has it, and the day it turns back into a problem."""
    from datetime import date
    data = healthy(tmp_path)
    drilled(data)
    _cpi_gap(data, last=date(2026, 9, 1))
    (data / "macro").mkdir(exist_ok=True)
    (data / "macro" / "us-calendar.json").write_text(json.dumps({"events": [
        {"kind": "cpi", "et": "2026-12-10T08:30:00-05:00", "detail": "November 2026", "source": "https://www.bls.gov/schedule/news_release/cpi.htm"}]}),
        encoding="utf-8")
    day = datetime(2026, 11, 22, 1, 0, tzinfo=timezone.utc)
    out = health_report(data, now=day)
    assert macro(out) == []
    assert out["known"] == [{"id": "gap:2026-10", "ids": ["macro:us_cpi_yoy", "macro:us_core_cpi_yoy"],
                             "label": "Lạm phát CPI của Mỹ (so cùng kỳ); Lạm phát CPI lõi của Mỹ (bỏ lương thực, năng lượng; so cùng kỳ)",
                             "detail": "tháng 10/2026 chưa tính được so cùng kỳ vì nguồn để trống số tháng 10/2025 (không tự lấp). Không cần làm gì: "
                                       "tự hết khi có số tháng 11/2026 (BLS hẹn công bố 10/12/2026); đến 15/12/2026 vẫn chưa có thì báo lại thành sự cố."}]
    (data / "macro" / "us-calendar.json").unlink()
    assert health_report(data, now=day)["known"][0]["detail"].endswith(
        "tự hết khi có số tháng 11/2026; đến 15/12/2026 vẫn chưa có thì báo lại thành sự cố.")
    late = health_report(data, now=datetime(2026, 12, 16, 1, 0, tzinfo=timezone.utc))
    assert late["known"] == [] and macro(late) == ["macro:us_cpi_yoy", "macro:us_core_cpi_yoy"]


def test_a_gap_that_does_not_explain_the_whole_age_stays_a_problem(tmp_path):
    from datetime import date
    data = healthy(tmp_path)
    drilled(data)
    _cpi_gap(data, last=date(2026, 8, 1))  # September is missing too: not the blank year-ago month
    out = health_report(data, now=datetime(2026, 11, 22, 1, 0, tzinfo=timezone.utc))
    assert out["known"] == [] and set(macro(out)) == {"macro:us_cpi_yoy", "macro:us_core_cpi_yoy"}


def test_a_problem_turned_known_is_not_announced_as_recovered_and_a_new_known_one_is_not_sent(tmp_path):
    problems = [{"id": "macro:us_cpi_yoy", "label": "CPI", "detail": "x"}]
    alert_changes(problems, tmp_path, save=True)
    known = [{"id": "gap:2026-10", "ids": ["macro:us_cpi_yoy", "macro:us_core_cpi_yoy"], "label": "CPI", "detail": "y"}]
    assert alert_changes([], tmp_path, save=True, known=known) == ([], [])
    assert alert_changes([], tmp_path, save=False) == ([], ["macro:us_cpi_yoy"])  # the gap over and the figure back: said once


def test_a_session_indicator_problem_names_the_hose_sessions_missed(tmp_path):
    from datetime import date
    from investment_agent.market.leading import MacroStore
    data = healthy(tmp_path)
    drilled(data)
    MacroStore(data).upsert("vnindex_value", [(date(2026, 11, 4), "20000")], entry="auto")  # Wednesday; 9/11 is Monday: 5, 6, 9 missed
    detail = next(p for p in report(data)["problems"] if p["id"] == "macro:vnindex_value")["detail"]
    assert detail == "số mới nhất ngày 04/11/2026, đã 3 phiên HOSE chưa có số mới (hạn 2 phiên)"


def test_a_known_problem_past_its_date_is_announced_again_owner_review_22_11_2026(tmp_path):
    """The Đã biết line promises "đến … vẫn chưa có thì báo lại thành sự cố": a problem announced, then known, then past its date is
    sent again; the gap over with the figure back is said recovered once."""
    problem = [{"id": "macro:us_cpi_yoy", "label": "CPI", "detail": "x"}]
    known = [{"id": "gap:2026-10", "ids": ["macro:us_cpi_yoy"], "label": "CPI", "detail": "y"}]
    alert_changes(problem, tmp_path, save=True)                      # 20/11: announced
    assert alert_changes([], tmp_path, save=True, known=known) == ([], [])  # 22/11: known, not recovered
    new, back = alert_changes(problem, tmp_path, save=False)         # 16/12: past its date
    assert [p["id"] for p in new] == ["macro:us_cpi_yoy"] and back == []
    assert alert_changes([], tmp_path, save=False) == ([], ["macro:us_cpi_yoy"])  # figure back instead: recovered once


def test_a_damaged_us_calendar_never_breaks_the_report(tmp_path):
    from datetime import date
    data = healthy(tmp_path)
    drilled(data)
    _cpi_gap(data, last=date(2026, 9, 1))
    (data / "macro" / "us-calendar.json").write_text("{not json", encoding="utf-8")
    out = health_report(data, now=datetime(2026, 11, 22, 1, 0, tzinfo=timezone.utc))
    assert out["known"][0]["detail"].endswith("tự hết khi có số tháng 11/2026; đến 15/12/2026 vẫn chưa có thì báo lại thành sự cố.")


def test_chi_so_nganh_is_as_old_as_the_oldest_watched_financial_ticker_not_the_newest_file(tmp_path):
    # since every HOSE bank and broker is fetched (27/11/2026), a fresh unwatched file must not hide a watched one gone stale
    data = healthy(tmp_path)
    (data / "market-symbols.txt").write_text("VCB\nFPT\n", encoding="utf-8")
    (data / "industries.json").write_text(json.dumps({"as_of": "x", "source": "t", "level": 2,
                                                      "sectors": {"VCB": "Ngân hàng", "FPT": "Công nghệ Thông tin"}}), encoding="utf-8")
    for name, days in (("VCB.json", 6), ("ACB.json", 0)):
        f = data / "financial-ratios" / name
        f.write_text("{}", encoding="utf-8")
        os.utime(f, (NOW.timestamp() - days * 86400 - 60, NOW.timestamp() - days * 86400 - 60))
    row = next(s for s in report(data)["sources"] if s["id"] == "financial-ratios")
    assert row["stale"] is True
    os.utime(data / "financial-ratios" / "VCB.json", (NOW.timestamp() - 3600, NOW.timestamp() - 3600))
    assert next(s for s in report(data)["sources"] if s["id"] == "financial-ratios")["stale"] is False


def test_foreign_and_proprietary_stores_are_late_past_five_closed_sessions_without_a_new_one(tmp_path):
    data = healthy(tmp_path)
    for folder, day in (("foreign", "2026-11-05"), ("proprietary", "2026-10-30")):
        (data / folder / "2026-11-09.json").unlink()
        (data / folder / f"{day}.json").write_text(json.dumps({"date": day, "stocks": {}}), encoding="utf-8")
    (data / "proprietary" / "2026-11-03.json").write_text(json.dumps({"date": "2026-11-03", "thieu": True}), encoding="utf-8")  # no figures
    rows = {s["id"]: s for s in report(data)["sources"]}
    assert rows["foreign"]["max_sessions"] == 5 and rows["foreign"]["last"] == "2026-11-05"
    assert rows["foreign"]["stale"] is False  # NOW is 9/11 15:00 in Vietnam: 6 and 9/11 closed since, 2 sessions
    assert rows["proprietary"]["stale"] is True and rows["proprietary"]["last"] == "2026-10-30"  # 2–9/11: 6 sessions
    problem = next(p for p in report(data)["problems"] if p["id"] == "source:proprietary")
    assert problem["label"] == "Tự doanh theo phiên" and "chậm 6 phiên" in problem["detail"]


def test_valuation_history_counts_tickers_past_fourteen_days_and_alerts_only_from_5_december(tmp_path):
    data = healthy(tmp_path)
    for name, days in (("OLD.json", 20), ("MID.json", 15), ("NEW.json", 3)):
        f = data / "index-history" / name
        f.write_text("{}", encoding="utf-8")
        os.utime(f, (NOW.timestamp() - days * 86400, NOW.timestamp() - days * 86400))
    row = next(s for s in report(data)["sources"] if s["id"] == "index-history")
    assert row["stale"] is True and row["max_days"] == 14 and row["over"] == 2 and row["oldest"] == "OLD"
    assert not any(p["id"] == "source:index-history" for p in report(data)["problems"])  # 9/11: before the first full refresh
    late = health_report(data, now=datetime(2026, 12, 5, 1, 0, tzinfo=timezone.utc))
    problem = next(p for p in late["problems"] if p["id"] == "source:index-history")
    assert "mã quá 14 ngày" in problem["detail"]


def test_the_remote_connector_is_checked_only_when_it_is_set_up(tmp_path):
    data = healthy(tmp_path)
    assert not any(s["id"] == "mcp-remote" for s in health_report(data, now=NOW, env={})["sources"])
    asked = []
    down = health_report(data, now=NOW, env={"MCP_REMOTE_SECRET": "s" * 40}, probe=lambda url: asked.append(url) or False)
    assert asked == [f"http://127.0.0.1:8770/{'s' * 40}/healthz"]
    row = next(s for s in down["sources"] if s["id"] == "mcp-remote")
    assert row["stale"] is True and row["label"] == "Kết nối từ xa"
    assert next(p for p in down["problems"] if p["id"] == "source:mcp-remote")["detail"].startswith("không trả lời")
    up = health_report(data, now=NOW, env={"MCP_REMOTE_SECRET": "s" * 40}, probe=lambda url: True)
    assert next(s for s in up["sources"] if s["id"] == "mcp-remote")["stale"] is False
    assert "s" * 40 not in str(up)  # the secret never appears in the report
