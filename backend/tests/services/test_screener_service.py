import json
from datetime import date, datetime, timedelta

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.domain.screener import ScreenError
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.screener import change_screens, foreign_by_symbol, read_screens, screen_check_run

OWNER = OwnerContext("owner-1", "owner", "test")
NOW = datetime(2026, 11, 2, 13, 0)


def _repo():
    return PersonalRepository("owner-1", MemoryDocumentStore())


def test_foreign_flows_come_from_the_session_snapshots_in_date_order(tmp_path):
    brief = tmp_path / "brief"
    brief.mkdir()
    for i in range(3):
        day = (date(2026, 10, 27) + timedelta(days=i)).isoformat()
        board = {"status": "ok", "symbols": {"FPT": {"foreign_net_bn": str(i)}, "HPG": {"price": 1}}}  # HPG from before the field existed
        (brief / f"{day}.json").write_text(json.dumps({"session_date": day, "board": board}), encoding="utf-8")
    (brief / "2026-10-30.json").write_text(json.dumps({"session_date": "2026-10-30", "board": {"status": "missing"}}), encoding="utf-8")
    assert foreign_by_symbol(tmp_path) == {"sessions": ["2026-10-27", "2026-10-28", "2026-10-29"],
                                           "values": {"FPT": {"2026-10-27": "0", "2026-10-28": "1", "2026-10-29": "2"}}}


def test_screens_are_saved_and_deleted_with_versions():
    repo = _repo()
    screens, version = change_screens(repo, OWNER, {"action": "save", "screen": {"name": "Rẻ", "criteria": {"verdict": ["cheap"]}, "notify": True}},
                                      expected_version=0, request_id="s1")
    assert version == 1 and screens[0]["name"] == "Rẻ"
    sid = screens[0]["id"]
    screens, version = change_screens(repo, OWNER, {"action": "save", "screen": {"id": sid, "name": "Rẻ hơn", "criteria": {"verdict": ["cheap"]}}},
                                      expected_version=1, request_id="s2")
    assert [s["name"] for s in screens] == ["Rẻ hơn"] and screens[0]["notify"] is False
    screens, version = change_screens(repo, OWNER, {"action": "delete", "id": sid}, expected_version=2, request_id="s3")
    assert screens == [] and read_screens(repo, OWNER) == ([], 3)
    with pytest.raises(ScreenError):
        change_screens(repo, OWNER, {"action": "delete", "id": "nope"}, expected_version=3, request_id="s4")


def _row(symbol, verdict):
    return {"symbol": symbol, "values": {"verdict": verdict}, "missing": {}, "foreign20_bn": None}


def test_new_tickers_in_a_notifying_screen_are_sent_once_after_a_baseline(tmp_path):
    repo = _repo()
    change_screens(repo, OWNER, {"action": "save", "screen": {"name": "Rẻ", "criteria": {"verdict": ["cheap"]}, "notify": True}},
                   expected_version=0, request_id="s1")
    change_screens(repo, OWNER, {"action": "save", "screen": {"name": "Lặng", "criteria": {"verdict": ["fair"]}, "notify": False}},
                   expected_version=1, request_id="s2")
    box = []
    send = lambda t: box.append(t) or True  # noqa: E731
    first = screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap")], send=send, now=NOW)
    assert first == {"status": "ok", "screens": 1, "entered": 0, "sent": False} and box == []
    second = screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap"), _row("HPG", "cheap"), _row("VCB", "fair")], send=send, now=NOW)
    assert second["entered"] == 1 and second["sent"] is True
    assert "Bộ lọc “Rẻ”: HPG" in box[0] and "Định giá: Rẻ" in box[0] and "Không phải khuyến nghị" in box[0] and "VCB" not in box[0]
    assert screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap"), _row("HPG", "cheap")], send=send, now=NOW)["entered"] == 0
    failed = screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap"), _row("HPG", "cheap"), _row("SSI", "cheap")], send=lambda t: False,
                              now=NOW)
    assert failed["sent"] is False
    assert screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap"), _row("HPG", "cheap"), _row("SSI", "cheap")], send=send,
                            now=NOW)["entered"] == 1  # offered again after a failed send


def test_changing_a_screens_criteria_starts_a_new_baseline(tmp_path):
    repo = _repo()
    screens, v = change_screens(repo, OWNER, {"action": "save", "screen": {"name": "Rẻ", "criteria": {"verdict": ["cheap"]}, "notify": True}},
                                expected_version=0, request_id="s1")
    box = []
    send = lambda t: box.append(t) or True  # noqa: E731
    screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap")], send=send, now=NOW)
    change_screens(repo, OWNER, {"action": "save", "screen": {"id": screens[0]["id"], "name": "Rẻ", "criteria": {"verdict": ["cheap", "fair"]},
                                                              "notify": True}}, expected_version=v, request_id="s2")
    out = screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap"), _row("HPG", "fair")], send=send, now=NOW)
    assert out["entered"] == 0 and box == []


def _lacking(symbol):
    return {"symbol": symbol, "values": {"verdict": None}, "missing": {"verdict": "x"}, "foreign20_bn": None}


def test_a_ticker_lacking_data_keeps_its_place_instead_of_leaving_and_reentering(tmp_path):
    repo = _repo()
    change_screens(repo, OWNER, {"action": "save", "screen": {"name": "Rẻ", "criteria": {"verdict": ["cheap"]}, "notify": True}},
                   expected_version=0, request_id="s1")
    box = []
    send = lambda t: box.append(t) or True  # noqa: E731
    screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap")], send=send, now=NOW)
    screen_check_run(repo, OWNER, tmp_path, rows=[_lacking("FPT")], send=send, now=NOW)  # a day without valuation
    assert screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap")], send=send, now=NOW)["entered"] == 0 and box == []


def test_with_delivery_off_or_no_notifying_screen_the_matches_are_still_recorded(tmp_path):
    repo = _repo()
    screens, v = change_screens(repo, OWNER, {"action": "save", "screen": {"name": "Rẻ", "criteria": {"verdict": ["cheap"]}, "notify": True}},
                                expected_version=0, request_id="s1")
    box = []
    send = lambda t: box.append(t) or True  # noqa: E731
    screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap")], send=send, now=NOW)
    out = screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap"), _row("HPG", "cheap")], send=None, now=NOW)  # delivery off
    assert out["sent"] is False and out["entered"] == 1
    assert screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap"), _row("HPG", "cheap")], send=send, now=NOW)["entered"] == 0
    change_screens(repo, OWNER, {"action": "save", "screen": {**screens[0], "notify": False}}, expected_version=v, request_id="s2")
    screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap")], send=send, now=NOW)
    change_screens(repo, OWNER, {"action": "save", "screen": {**screens[0], "notify": True}}, expected_version=v + 1, request_id="s3")
    assert screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap"), _row("SSI", "cheap")], send=send, now=NOW)["entered"] == 0  # baseline
    assert box == []


def test_a_corrupt_state_file_starts_a_baseline_and_the_note_shows_hanoi_time(tmp_path):
    from datetime import timezone
    repo = _repo()
    change_screens(repo, OWNER, {"action": "save", "screen": {"name": "Rẻ", "criteria": {"verdict": ["cheap"]}, "notify": True}},
                   expected_version=0, request_id="s1")
    (tmp_path / "alerts").mkdir()
    (tmp_path / "alerts" / "screens.json").write_text("{oops", encoding="utf-8")
    box = []
    send = lambda t: box.append(t) or True  # noqa: E731
    assert screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap")], send=send, now=NOW)["entered"] == 0
    utc = datetime(2026, 11, 2, 8, 30, tzinfo=timezone.utc)  # 15:30 in Hà Nội
    screen_check_run(repo, OWNER, tmp_path, rows=[_row("FPT", "cheap"), _row("HPG", "cheap")], send=send, now=utc)
    assert "15:30 02/11" in box[0]
