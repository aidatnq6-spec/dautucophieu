from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.domain.thesis import ThesisError
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.journal import read_journal
from investment_agent.services.theses import facts_for, hold, read_theses, save, thesis_check_run

OWNER = OwnerContext("owner-1", "owner", "test")
TODAY = date(2026, 11, 2)
NOW = datetime(2026, 11, 2, 13, 0)
D = Decimal


def _repo():
    return PersonalRepository("owner-1", MemoryDocumentStore())


def _data(tmp_path, closes=(60.0, 50.0, 40.0)):
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(2026, 10, 28) + timedelta(days=i), str(c)) for i, c in enumerate(closes)])
    return tmp_path


FOMO = {"reasons": ["fomo"], "note": "Ai cũng mua", "conditions": [{"kind": "loss_vs_cost", "params": {"pct": "10"}}]}


def _facts(tmp_path, cost="50000"):
    return facts_for(tmp_path, "FPT", cost=D(cost), row={"fair": "60000", "quality": {"reason": None, "f_score": {"kind": "f_score", "score": 5,
                                                                                                                 "year": "2025"}}},
                     chains=["neutral"], deals=[])


def test_facts_come_from_stored_closes_valuation_and_statements(tmp_path):
    f = _facts(_data(tmp_path))
    assert f["close"] == D("40000") and f["price"] == D("40000") and f["cost"] == D("50000") and f["fair"] == D("60000")
    assert f["quality"]["score"] == 5 and f["chains"] == ["neutral"] and f["insider_deals"] == [] and len(f["daily"]) == 3
    live = facts_for(tmp_path, "FPT", cost=D("50000"), row=None, chains=None, deals=None, live=D("41000"))
    assert live["price"] == D("41000") and live["fair"] is None and live["quality"] is None and live["insider_deals"] is None


def test_a_thesis_is_saved_for_a_held_ticker_once_with_a_journal_entry(tmp_path):
    repo = _repo()
    theses, version = save(repo, OWNER, symbol="FPT", raw=FOMO, company="other", facts=_facts(_data(tmp_path)), today=TODAY,
                           expected_version=0, request_id="t1", held={"FPT"})
    assert version == 1 and theses[0]["symbol"] == "FPT" and theses[0]["snapshot"] == {"price": "40000", "cost": "50000", "fair": "60000",
                                                                                        "f_score": 5}
    entry = read_journal(repo, OWNER)[0][0]
    assert entry.kind == "buy" and entry.emotion == "fomo" and "Sợ bỏ lỡ" in entry.reason and "Ai cũng mua" in entry.reason
    for symbol, held, code in (("FPT", {"FPT"}, "thesis_exists"), ("HPG", {"FPT"}, "not_held")):
        with pytest.raises(ThesisError) as err:
            save(repo, OWNER, symbol=symbol, raw=FOMO, company="other", facts=_facts(tmp_path), today=TODAY, expected_version=1,
                 request_id="t2", held=held)
        assert err.value.code == code


def _sent():
    box = []
    return box, (lambda text: box.append(text) or True)


def test_a_broken_condition_is_reported_with_why_the_history_scenario_and_no_forecast(tmp_path):
    repo, data = _repo(), _data(tmp_path)
    save(repo, OWNER, symbol="FPT", raw=FOMO, company="other", facts=_facts(data), today=TODAY, expected_version=0, request_id="t1", held={"FPT"})
    box, send = _sent()
    out = thesis_check_run(repo, OWNER, data, scope="data", facts={"FPT": _facts(data)}, shares={"FPT": 1000}, held={"FPT"}, send=send,
                           now=NOW, today=TODAY, request_id="c1")
    assert out == {"status": "ok", "open": 1, "closed": 0, "events": 1, "sent": True}
    text = box[0]
    assert "FPT — Lỗ so với giá vốn (10%)" in text and "giá 40,00 so với giá vốn 50,00 (−20,0%)" in text
    assert "“Ai cũng mua”" in text and "Lý do mua: Sợ bỏ lỡ" in text
    assert "kịch bản từ lịch sử, không phải dự báo" in text and "−33,3%" in text and "13.332.000 đ" in text  # 60 → 40 (−33,33%), on 1000 shares at 40,00
    assert "sẽ lỗ" not in text and "Không phải khuyến nghị. Phần mềm không đặt lệnh." in text
    box2, send2 = _sent()
    thesis_check_run(repo, OWNER, data, scope="data", facts={"FPT": _facts(data)}, shares={"FPT": 1000}, held={"FPT"}, send=send2, now=NOW,
                     today=TODAY, request_id="c2")
    assert box2 == []  # reported once


def test_a_failed_delivery_is_offered_again_and_a_sold_ticker_closes_its_thesis(tmp_path):
    repo, data = _repo(), _data(tmp_path)
    save(repo, OWNER, symbol="FPT", raw=FOMO, company="other", facts=_facts(data), today=TODAY, expected_version=0, request_id="t1", held={"FPT"})
    out = thesis_check_run(repo, OWNER, data, scope="data", facts={"FPT": _facts(data)}, shares={"FPT": 1000}, held={"FPT"}, send=lambda t: False,
                           now=NOW, today=TODAY, request_id="c1")
    assert out["sent"] is False and read_theses(repo, OWNER)[0][0]["conditions"][0]["sent_first"] is False
    box, send = _sent()
    thesis_check_run(repo, OWNER, data, scope="data", facts={"FPT": _facts(data)}, shares={"FPT": 1000}, held={"FPT"}, send=send, now=NOW,
                     today=TODAY, request_id="c2")
    assert len(box) == 1
    out = thesis_check_run(repo, OWNER, data, scope="data", facts={}, shares={}, held=set(), send=send, now=NOW, today=TODAY + timedelta(days=1),
                           request_id="c3")
    assert out["closed"] == 1 and read_theses(repo, OWNER)[0][0]["closed_on"] == "2026-11-03"


def test_the_price_scope_checks_only_price_conditions(tmp_path):
    repo, data = _repo(), _data(tmp_path)
    raw = {"reasons": ["cheap"], "note": "", "conditions": [{"kind": "loss_vs_cost", "params": {"pct": "10"}},
                                                            {"kind": "f_score", "params": {"n": 3}}]}
    save(repo, OWNER, symbol="FPT", raw=raw, company="other", facts=_facts(data), today=TODAY, expected_version=0, request_id="t1", held={"FPT"})
    box, send = _sent()
    thesis_check_run(repo, OWNER, data, scope="price", facts={"FPT": _facts(data)}, shares={"FPT": 1000}, held={"FPT"}, send=send, now=NOW,
                     today=TODAY, request_id="c1")
    statuses = [c["status"] for c in read_theses(repo, OWNER)[0][0]["conditions"]]
    assert statuses == ["broken", "ok"] and "F-Score" not in box[0]  # both recorded on save; only the price one is due a note


def test_holding_on_writes_the_reason_to_the_journal(tmp_path):
    repo, data = _repo(), _data(tmp_path)
    theses, v = save(repo, OWNER, symbol="FPT", raw=FOMO, company="other", facts=_facts(data), today=TODAY, expected_version=0, request_id="t1",
                     held={"FPT"})
    thesis_check_run(repo, OWNER, data, scope="data", facts={"FPT": _facts(data)}, shares={"FPT": 1000}, held={"FPT"}, send=lambda t: True,
                     now=NOW, today=TODAY, request_id="c1")
    theses, v = read_theses(repo, OWNER)
    cond = theses[0]["conditions"][0]["id"]
    theses, v = hold(repo, OWNER, thesis_id=theses[0]["id"], cond_id=cond, reason="Chờ KQKD quý 4", emotion="anxious", until=TODAY + timedelta(days=30),
                     new_condition=None, company="other", fair=None, today=TODAY, expected_version=v, request_id="h1")
    assert theses[0]["conditions"][0]["hold"]["until"] == "2026-12-02"
    entry = read_journal(repo, OWNER)[0][-1]
    assert entry.kind == "hold" and entry.emotion == "anxious" and "Chờ KQKD quý 4" in entry.reason and theses[0]["history"][-1]["entry_id"] == entry.entry_id


def test_the_in_session_check_reads_nothing_outside_the_session(tmp_path, capsys):
    import json
    from datetime import timezone

    from investment_agent.cli import thesis_check_cli
    assert thesis_check_cli(tmp_path, tmp_path / "calendar.json", "price", now=datetime(2026, 10, 31, 3, 30, tzinfo=timezone.utc)) == 0  # Saturday
    assert json.loads(capsys.readouterr().out) == {"status": "skipped", "reason": "outside_session"}


def test_a_check_that_only_moves_readings_does_not_rewrite_the_record(tmp_path):
    repo, data = _repo(), _data(tmp_path)
    raw = {"reasons": ["cheap"], "note": "", "conditions": [{"kind": "loss_vs_cost", "params": {"pct": "50"}}]}
    _, version = save(repo, OWNER, symbol="FPT", raw=raw, company="other", facts=_facts(data), today=TODAY, expected_version=0, request_id="t1",
                      held={"FPT"})
    for i, price in enumerate(("41000", "42000")):
        live = facts_for(data, "FPT", cost=D("50000"), row=None, chains=None, deals=None, live=D(price))
        thesis_check_run(repo, OWNER, data, scope="price", facts={"FPT": live}, shares={"FPT": 1000}, held={"FPT"}, send=lambda t: True,
                         now=NOW, today=TODAY, request_id=f"c{i}")
    assert read_theses(repo, OWNER)[1] == version  # the page's version stays valid while only the price moves


def test_without_a_matched_price_the_in_session_check_does_not_use_the_last_close(tmp_path):
    f = facts_for(_data(tmp_path), "FPT", cost=D("50000"), row=None, chains=None, deals=None, live=None, live_only=True)
    assert f["price"] is None and f["close"] == D("40000")


def test_journal_entries_are_written_first_under_ids_from_the_request_so_a_retry_does_not_lose_or_double_them(tmp_path, monkeypatch):
    import investment_agent.services.theses as svc
    from investment_agent.repositories.personal import RepositoryUnavailable
    repo, data = _repo(), _data(tmp_path)
    real, calls = svc.append_entry, []

    def flaky(*a, **k):  # the journal write fails once, as when Firestore drops a request
        calls.append(1)
        if len(calls) == 1:
            raise RepositoryUnavailable("down")
        return real(*a, **k)
    monkeypatch.setattr(svc, "append_entry", flaky)
    with pytest.raises(RepositoryUnavailable):
        save(repo, OWNER, symbol="FPT", raw=FOMO, company="other", facts=_facts(data), today=TODAY, expected_version=0, request_id="t1", held={"FPT"})
    save(repo, OWNER, symbol="FPT", raw=FOMO, company="other", facts=_facts(data), today=TODAY, expected_version=0, request_id="t1", held={"FPT"})
    assert [e.kind for e in read_journal(repo, OWNER)[0]] == ["buy"]
    theses, v = read_theses(repo, OWNER)
    calls.clear()
    args = dict(thesis_id=theses[0]["id"], cond_id=theses[0]["conditions"][0]["id"], reason="Chờ", emotion=None, until=TODAY + timedelta(days=10),
                new_condition=None, company="other", fair=None, today=TODAY, expected_version=v, request_id="h1")
    with pytest.raises(RepositoryUnavailable):
        hold(repo, OWNER, **args)
    theses, _ = hold(repo, OWNER, **args)
    holds = [e for e in read_journal(repo, OWNER)[0] if e.kind == "hold"]
    assert len(holds) == 1 and theses[0]["history"][-1]["entry_id"] == holds[0].entry_id


def test_with_delivery_off_the_check_still_records_and_closes_but_marks_nothing_sent(tmp_path):
    repo, data = _repo(), _data(tmp_path)
    save(repo, OWNER, symbol="FPT", raw=FOMO, company="other", facts=_facts(data), today=TODAY, expected_version=0, request_id="t1", held={"FPT"})
    out = thesis_check_run(repo, OWNER, data, scope="data", facts={"FPT": _facts(data)}, shares={"FPT": 1000}, held={"FPT"}, send=None, now=NOW,
                           today=TODAY, request_id="c1")
    assert out["sent"] is False and read_theses(repo, OWNER)[0][0]["conditions"][0]["sent_first"] is False
    out = thesis_check_run(repo, OWNER, data, scope="price", facts={}, shares={}, held=set(), send=None, now=NOW, today=TODAY, request_id="c2")
    assert out["closed"] == 1


def test_the_owners_lesson_is_added_to_the_first_note_when_there_is_one(tmp_path):
    repo, data = _repo(), _data(tmp_path)
    save(repo, OWNER, symbol="FPT", raw=FOMO, company="other", facts=_facts(data), today=TODAY, expected_version=0, request_id="t1", held={"FPT"})
    box, send = _sent()
    thesis_check_run(repo, OWNER, data, scope="data", facts={"FPT": _facts(data)}, shares={"FPT": 1000}, held={"FPT"}, send=send, now=NOW,
                     today=TODAY, request_id="c1", lesson=lambda t, c: "5 lần trước bạn giữ tiếp")
    assert "• Bài học của chính bạn: 5 lần trước bạn giữ tiếp" in box[0]
