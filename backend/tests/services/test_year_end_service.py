from datetime import date, datetime, timezone

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.year_end import YearEndError, gather_facts, remind_run, tick, view

OWNER = OwnerContext("owner-1", "owner", "test")
LEFT = {"theses": (False, "chưa rà trong 90 ngày: BBB"), "tower": (True, ""), "calendar": (True, ""), "drill": (True, ""), "goals": (True, "")}


def repo():
    return PersonalRepository("owner-1", MemoryDocumentStore())


def test_no_list_outside_december_and_january():
    assert view(repo(), OWNER, today=date(2026, 11, 22), facts=LEFT) == {"open": False, "opens_on": "2026-12-01"}


def test_the_owner_ticks_and_unticks_a_manual_item_and_the_version_moves():
    r = repo()
    out = view(r, OWNER, today=date(2026, 12, 2), facts=LEFT)
    assert out["open"] is True and out["version"] == 0 and out["left"] == 3
    out = tick(r, OWNER, today=date(2026, 12, 2), item="dividends", done=True, expected_version=0, request_id="t1", facts=LEFT)
    assert out["version"] == 1 and out["left"] == 2
    out = tick(r, OWNER, today=date(2026, 12, 3), item="dividends", done=False, expected_version=1, request_id="t2", facts=LEFT)
    assert out["left"] == 3
    with pytest.raises(YearEndError):
        tick(r, OWNER, today=date(2026, 12, 3), item="tower", done=True, expected_version=2, request_id="t3", facts=LEFT)  # the app checks it
    with pytest.raises(YearEndError):
        tick(r, OWNER, today=date(2026, 11, 3), item="dividends", done=True, expected_version=2, request_id="t4", facts=LEFT)  # not open


def test_reminds_once_a_day_on_the_list_and_retries_a_failed_send():
    r, sent = repo(), []
    keep = lambda t: sent.append(t) or True  # noqa: E731
    assert remind_run(r, OWNER, today=date(2026, 11, 30), send=keep, request_id="a", facts=LEFT) == {"due": None, "sent": False}
    assert remind_run(r, OWNER, today=date(2026, 12, 1), send=lambda t: False, request_id="b", facts=LEFT) == {"due": "2026-12-01", "sent": False}
    assert remind_run(r, OWNER, today=date(2026, 12, 2), send=keep, request_id="c", facts=LEFT) == {"due": "2026-12-01", "sent": True}
    assert remind_run(r, OWNER, today=date(2026, 12, 3), send=keep, request_id="d", facts=LEFT) == {"due": None, "sent": False}
    assert len(sent) == 1 and sent[0].startswith("Việc cuối năm 2026: còn 3 việc")
    done = {k: (True, "") for k in LEFT}
    tick(r, OWNER, today=date(2026, 12, 5), item="dividends", done=True, expected_version=1, request_id="e", facts=done)
    tick(r, OWNER, today=date(2026, 12, 5), item="cashflow", done=True, expected_version=2, request_id="f", facts=done)
    assert remind_run(r, OWNER, today=date(2026, 12, 20), send=keep, request_id="g", facts=done) == {"due": "2026-12-20", "sent": False, "left": 0}
    assert len(sent) == 1  # nothing left: no note


def test_gathering_the_checks_never_fails_and_names_what_it_could_not_read(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "trading-calendar-hose-2027.json").write_text("{}", encoding="utf-8")
    facts = gather_facts(repo(), OWNER, data_dir=tmp_path / "data", config_dir=tmp_path / "config", today=date(2026, 12, 2),
                         now=datetime(2026, 12, 2, 1, tzinfo=timezone.utc), quotes={})
    assert facts["theses"] == (True, "không giữ mã nào")
    assert facts["calendar"] == (True, "đã có lịch 2027")
    assert facts["drill"] == (False, "chưa diễn tập lần nào")
    assert facts["goals"] == (False, "chưa đặt mục tiêu 2027")
    assert facts["tower"][0] is None


def test_the_month_end_snapshot_is_the_last_day_written_in_each_month_and_keeps_only_totals():
    from investment_agent.services.year_end import read_snapshots, snapshot_run
    r = repo()
    pyramid = {"total": "1000", "base": "900", "layers": [{"id": "deposit", "amount": "400", "status": "ok", "share": "0.4"},
                                                          {"id": "stocks", "amount": "600", "status": "ok", "share": "0.6"}]}
    assert snapshot_run(r, OWNER, pyramid=pyramid, today=date(2026, 11, 29), request_id="s1") == {"month": "2026-11", "written": True}
    assert snapshot_run(r, OWNER, pyramid=pyramid, today=date(2026, 11, 29), request_id="s2") == {"month": "2026-11", "written": False}  # once a day
    later = {**pyramid, "total": "1100", "layers": [{**pyramid["layers"][0], "amount": "500"}, pyramid["layers"][1]]}
    snapshot_run(r, OWNER, pyramid=later, today=date(2026, 11, 30), request_id="s3")
    snapshot_run(r, OWNER, pyramid=pyramid, today=date(2026, 12, 1), request_id="s4")
    snaps = read_snapshots(r, OWNER)
    assert snaps["2026-11"] == {"taken_on": "2026-11-30", "total": "1100", "layers": {"deposit": "500", "stocks": "600"}}
    assert snaps["2026-12"]["taken_on"] == "2026-12-01"
    assert snapshot_run(r, OWNER, pyramid=None, today=date(2026, 12, 2), request_id="s5") == {"month": "2026-12", "written": False, "reason": "no_pyramid"}


def test_the_drill_date_is_said_in_vietnam_time(tmp_path):
    import json
    (tmp_path / "data" / "alerts").mkdir(parents=True)
    (tmp_path / "data" / "alerts" / "restore-drill.json").write_text(json.dumps({"at": "2026-11-30T23:00:00+00:00", "ok": True}), encoding="utf-8")
    facts = gather_facts(repo(), OWNER, data_dir=tmp_path / "data", config_dir=tmp_path, today=date(2026, 12, 2),
                         now=datetime(2026, 12, 2, 1, tzinfo=timezone.utc), quotes={})
    assert facts["drill"] == (True, "lần gần nhất 01/12/2026")  # 06:00 on 1 December in Vietnam
