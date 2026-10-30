from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from investment_agent.jobs.runner import JobStore, LeaseBusy
from investment_agent.jobs.schedule import ReportState, decide, report_kinds, scheduler_lease
from investment_agent.market.calendar import TradingCalendar

VN = ZoneInfo("Asia/Ho_Chi_Minh")
# 2026-09-02 (Wed) is a holiday in this synthetic calendar; 2026-10-30 is a Friday and the month's last session.
CAL = TradingCalendar(version="t", source="synthetic", holidays=frozenset({date(2026, 9, 2), date(2026, 9, 4)}),
                      first=date(2026, 8, 1), last=date(2026, 12, 31))


def at(day, hhmm):
    h, m = map(int, hhmm.split(":"))
    return datetime(*map(int, day.split("-")), h, m, tzinfo=VN)


def state(published=(), attempts=None):
    return ReportState(published=frozenset(date.fromisoformat(d) for d in published), attempts={date.fromisoformat(k): v for k, v in (attempts or {}).items()})


def test_nothing_before_first_slot():
    d = decide(at("2026-10-27", "15:29"), CAL, state(published=["2026-10-26"]))
    assert d.run is False and d.reason == "not_yet"


def test_first_slot_runs_todays_session():
    d = decide(at("2026-10-27", "15:30"), CAL, state(published=["2026-10-26"]))
    assert (d.run, d.session_date, d.attempt, d.send) == (True, date(2026, 10, 27), 1, True)


def test_retry_slots_depend_on_data_not_clock_spam():
    s1 = state(published=["2026-10-26"], attempts={"2026-10-27": 1})
    assert decide(at("2026-10-27", "17:30"), CAL, s1).run is False  # 15:30 tried; the only retry is at 20:00
    assert decide(at("2026-10-27", "20:00"), CAL, s1).attempt == 2
    s2 = state(published=["2026-10-26"], attempts={"2026-10-27": 2})
    d = decide(at("2026-10-27", "21:00"), CAL, s2)
    assert d.run is False and d.reason == "attempts_exhausted"


def test_morning_wakeup_only_catches_up_the_previous_session():
    d = decide(at("2026-10-28", "08:30"), CAL, state(published=["2026-10-26"], attempts={"2026-10-27": 1}))
    assert (d.run, d.reason, d.session_date, d.attempt) == (True, "catch_up", date(2026, 10, 27), 2)


def test_published_session_is_not_rerun():
    d = decide(at("2026-10-27", "20:05"), CAL, state(published=["2026-10-27"]))
    assert d.run is False and d.reason == "already_published"


def test_weekend_and_holiday_produce_no_new_session():
    d = decide(at("2026-09-02", "18:00"), CAL, state(published=["2026-09-01"]))
    assert d.run is False and d.reason == "already_published"  # holiday: latest session is 09-01
    d = decide(at("2026-10-31", "18:00"), CAL, state(published=["2026-10-30"]))
    assert d.run is False


def test_resume_catches_up_only_the_latest_missed_session_and_counts_others():
    d = decide(at("2026-10-26", "09:00"), CAL, state(published=["2026-10-21"]))  # Mon morning, missed Thu+Fri
    assert d.run is True and d.session_date == date(2026, 10, 23) and d.missed_sessions == 1
    assert d.send is True and d.reason == "catch_up"


def test_old_backfill_never_sends():
    d = decide(at("2026-10-26", "09:00"), CAL, state(published=["2026-10-21"]), backfill=date(2026, 10, 22))
    assert d.run is True and d.session_date == date(2026, 10, 22) and d.send is False


@pytest.mark.parametrize("session, kinds", [
    (date(2026, 10, 27), ("after_close",)),
    (date(2026, 10, 23), ("after_close", "weekly")),
    (date(2026, 9, 3), ("after_close", "weekly")),    # Friday 09-04 is a holiday: Thursday closes the week
    (date(2026, 10, 30), ("after_close", "weekly", "monthly")),
])
def test_weekly_and_monthly_follow_last_session(session, kinds):
    assert report_kinds(session, CAL) == kinds


def test_two_schedulers_cannot_run_the_same_tick(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite")
    now = at("2026-10-27", "17:30")
    scheduler_lease(store, now, worker_id="a")
    with pytest.raises(LeaseBusy):
        scheduler_lease(store, now, worker_id="b")


def test_naive_time_rejected():
    with pytest.raises(ValueError):
        decide(datetime(2026, 10, 27, 17, 30), CAL, state())


# --- tick wiring ---------------------------------------------------------------

from decimal import Decimal

from investment_agent.api.auth import OwnerContext
from investment_agent.jobs.schedule import scheduled_tick
from investment_agent.market.view import PricePoint, SyntheticMarket
from investment_agent.notifications.outbox import DeliveryStore, NotificationSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

OWNER = OwnerContext("owner-1", "owner", "scheduler")


class FakeSender:
    def __init__(self):
        self.sent = []

    def send(self, chat_id, text):
        from investment_agent.notifications.telegram import SendOutcome
        self.sent.append(text)
        return SendOutcome("sent", message_id=len(self.sent))


def tick(tmp_path, repo, now, sender=None, market=None):
    return scheduled_tick(repo=repo, owner=OWNER, market=market or SyntheticMarket(), jobs=JobStore(tmp_path / "jobs.sqlite"),
                          deliveries=DeliveryStore(tmp_path / "d.sqlite"), sender=sender, cal=CAL, now=now, worker_id="sched")


def test_tick_counts_attempts_and_stops_after_two_incomplete_runs(tmp_path):
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    for hhmm, expected in (("15:31", "incomplete"), ("16:00", None), ("17:31", None), ("20:01", "incomplete"), ("21:00", None)):
        result = tick(tmp_path, repo, at("2026-10-27", hhmm))
        assert (result.statuses[0] if result.statuses else None) == expected, hhmm


def test_tick_sends_only_when_scheduled_sending_is_enabled(tmp_path):
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    sender = FakeSender()
    market = SyntheticMarket(prices={"FPT": PricePoint(Decimal(1), date(2026, 10, 27))})
    # No profile: reports stay incomplete and are never queued, so nothing is sent even when enabled.
    settings = NotificationSettings(enabled=True, chat_id="-100123", members_may_view_personal_data=True, scheduled_enabled=True)
    repo.write(OWNER, "settings", "notifications", settings.model_dump(mode="json"), expected_version=0, request_id="n1")
    result = tick(tmp_path, repo, at("2026-10-27", "15:31"), sender=sender, market=market)
    assert result.statuses == ["incomplete"] and sender.sent == []


def test_cli_calendar_must_name_an_official_source(tmp_path):
    import json as _json
    from investment_agent.cli import load_calendar
    path = tmp_path / "cal.json"
    path.write_text(_json.dumps({"version": "x", "source": "synthetic", "holidays": [], "first": "2026-01-01", "last": "2026-12-31"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_calendar(path)
    path.write_text(_json.dumps({"version": "hose-2026", "source": "https://www.hsx.vn/...", "holidays": ["2026-09-02"], "first": "2026-01-01",
                                 "last": "2026-12-31"}), encoding="utf-8")
    assert not load_calendar(path).is_session(date(2026, 9, 2))



def test_morning_wake_up_only_catches_up_the_previous_session():
    d = decide(at("2026-10-27", "07:00"), CAL, state(published=["2026-10-26"]))
    assert d.run is False and d.reason == "not_yet"  # today's session has not traded yet
    d = decide(at("2026-10-27", "07:00"), CAL, state(published=["2026-10-23"]))
    assert (d.run, d.reason, d.session_date) == (True, "catch_up", date(2026, 10, 26))


def test_already_published_names_the_session():
    d = decide(at("2026-10-27", "20:05"), CAL, state(published=["2026-10-27"]))
    assert d.session_date == date(2026, 10, 27)


def test_a_manually_created_report_of_the_current_session_is_sent_on_the_next_wake_up(tmp_path, monkeypatch):
    """26/10/2026: the owner pressed Tạo bản tin before the 15:30 run; the scheduler then saw 'already_published' and never sent it."""
    import investment_agent.jobs.schedule as sched
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    settings = NotificationSettings(enabled=True, chat_id="-100123", members_may_view_personal_data=True, scheduled_enabled=True)
    repo.write(OWNER, "settings", "notifications", settings.model_dump(mode="json"), expected_version=0, request_id="n1")
    reports = {"today": {"report_id": "today", "report_kind": "after_close", "session_date": "2026-10-27", "status": "published"},
               "old": {"report_id": "old", "report_kind": "after_close", "session_date": "2026-10-26", "status": "published"}}
    monkeypatch.setattr(sched, "list_reports", lambda repo, owner: list(reports.values()))
    monkeypatch.setattr(sched, "get_report", lambda repo, owner, rid: reports.get(rid))
    sent = []

    def fake_deliver(report, settings, sender, store, market=None):
        sent.append(report["report_id"])
        return type("R", (), {"status": "sent", "parts_new": 1})()
    monkeypatch.setattr(sched, "deliver", fake_deliver)
    store = DeliveryStore(tmp_path / "d.sqlite")
    store.enqueue("old")
    store.enqueue("today")
    result = scheduled_tick(repo=repo, owner=OWNER, market=SyntheticMarket(), jobs=JobStore(tmp_path / "jobs.sqlite"), deliveries=store,
                            sender=FakeSender(), cal=CAL, now=at("2026-10-27", "17:31"), worker_id="sched")
    assert result.decision.reason == "already_published" and result.delivered == ["today"] and sent == ["today"]
    assert store.queued() == ["old"]  # an older session's report is not sent late


def test_queued_reports_are_rendered_with_their_sessions_market_snapshot(tmp_path, monkeypatch):
    import investment_agent.jobs.schedule as sched
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    settings = NotificationSettings(enabled=True, chat_id="-100123", members_may_view_personal_data=True, scheduled_enabled=True)
    repo.write(OWNER, "settings", "notifications", settings.model_dump(mode="json"), expected_version=0, request_id="n1")
    reports = {"today": {"report_id": "today", "report_kind": "after_close", "session_date": "2026-10-27", "status": "published"}}
    monkeypatch.setattr(sched, "list_reports", lambda repo, owner: list(reports.values()))
    monkeypatch.setattr(sched, "get_report", lambda repo, owner, rid: reports.get(rid))
    seen = []
    monkeypatch.setattr(sched, "deliver", lambda report, s, sender, store, market=None: seen.append(market) or type("R", (), {"status": "sent", "parts_new": 1})())
    store = DeliveryStore(tmp_path / "d.sqlite")
    store.enqueue("today")
    scheduled_tick(repo=repo, owner=OWNER, market=SyntheticMarket(), jobs=JobStore(tmp_path / "jobs.sqlite"), deliveries=store,
                   sender=FakeSender(), cal=CAL, now=at("2026-10-27", "17:31"), worker_id="sched",
                   market_for=lambda session: {"session_date": session})
    assert seen == [{"session_date": "2026-10-27"}]


def test_a_report_whose_parts_were_all_sent_before_is_not_counted_as_delivered_again(tmp_path, monkeypatch):
    """27/10/2026: the log said delivered 1 on every wake-up for a report already sent at 15:30, though nothing new went out."""
    import investment_agent.jobs.schedule as sched
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    settings = NotificationSettings(enabled=True, chat_id="-100123", members_may_view_personal_data=True, scheduled_enabled=True)
    repo.write(OWNER, "settings", "notifications", settings.model_dump(mode="json"), expected_version=0, request_id="n1")
    report = {"report_id": "today", "report_kind": "after_close", "session_date": "2026-10-27", "status": "published"}
    monkeypatch.setattr(sched, "list_reports", lambda repo, owner: [report])
    monkeypatch.setattr(sched, "get_report", lambda repo, owner, rid: report if rid == "today" else None)
    import investment_agent.notifications.outbox as outbox
    monkeypatch.setattr(outbox, "render_report", lambda report, market=None: "Bản tin")
    store, sender = DeliveryStore(tmp_path / "d.sqlite"), FakeSender()
    store.enqueue("today")
    assert outbox.deliver(report, settings, sender, store).status == "sent"  # sent outside the scheduler, e.g. by the owner from the app
    result = scheduled_tick(repo=repo, owner=OWNER, market=SyntheticMarket(), jobs=JobStore(tmp_path / "jobs.sqlite"), deliveries=store,
                            sender=sender, cal=CAL, now=at("2026-10-27", "17:31"), worker_id="sched")
    assert result.delivered == [] and len(sender.sent) == 1
    assert store.queued() == []  # still taken off the queue
