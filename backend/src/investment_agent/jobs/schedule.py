"""Scheduling decisions in Asia/Ho_Chi_Minh for after-close reports.

Slots 15:30 and 20:00 are attempts for one session, used only
while that session has no published report (late data), never repeated
identical sends. A report needs every holding priced for that session, so an
early slot that runs before the vendor's close simply leaves it to the next.
Wake-ups outside the slots (08:30, logon) only catch up an earlier session. After a missed day or a machine resume only the most recent
unpublished session is caught up; older ones are counted, and an explicit
historical backfill never sends. Weekly and monthly reports follow the last
trading session of the week or month in the calendar.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from investment_agent.services.records import notification_settings as current_settings
from investment_agent.market.calendar import TradingCalendar
from investment_agent.notifications.outbox import deliver

from .daily import run_after_close
from .publication import get_report, list_reports
from .runner import JobStore

VN = ZoneInfo("Asia/Ho_Chi_Minh")
SLOTS = (time(15, 30), time(20, 0))


@dataclass(frozen=True)
class ReportState:
    published: frozenset[date] = frozenset()
    attempts: dict[date, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    run: bool
    reason: str
    session_date: date | None = None
    attempt: int = 0
    send: bool = False
    missed_sessions: int = 0
    kinds: tuple[str, ...] = ()


def _previous_session(cal: TradingCalendar, day: date) -> date | None:
    d = day - timedelta(days=1)
    while d >= cal.first:
        if cal.is_session(d):
            return d
        d -= timedelta(days=1)
    return None


def _next_session(cal: TradingCalendar, day: date) -> date | None:
    d = day + timedelta(days=1)
    while d <= cal.last:
        if cal.is_session(d):
            return d
        d += timedelta(days=1)
    return None


def report_kinds(session: date, cal: TradingCalendar) -> tuple[str, ...]:
    nxt = _next_session(cal, session)
    kinds = ["after_close"]
    if nxt is None or nxt.isocalendar()[:2] != session.isocalendar()[:2]:
        kinds.append("weekly")
    if nxt is None or (nxt.year, nxt.month) != (session.year, session.month):
        kinds.append("monthly")
    return tuple(kinds)


def decide(now: datetime, cal: TradingCalendar, state: ReportState, *, backfill: date | None = None) -> Decision:
    if now.tzinfo is None:
        raise ValueError("scheduler time requires timezone")
    local = now.astimezone(VN)
    if backfill is not None:
        return Decision(True, "backfill", backfill, state.attempts.get(backfill, 0) + 1, send=False, kinds=report_kinds(backfill, cal))
    today = local.date()
    passed = sum(local.time() >= s for s in SLOTS)
    before_first_slot = cal.is_session(today) and not passed
    target = today if cal.is_session(today) and passed else _previous_session(cal, today)
    if target is None:
        return Decision(False, "no_session")
    if target in state.published:
        return Decision(False, "not_yet") if before_first_slot else Decision(False, "already_published", target)
    last_published = max((d for d in state.published if d < target), default=None)
    missed = 0
    if last_published is not None:
        missed = sum(1 for d in cal.sessions(last_published + timedelta(days=1), target) if d < target and d not in state.published)
    attempts = state.attempts.get(target, 0)
    if attempts >= len(SLOTS):
        return Decision(False, "attempts_exhausted", target, attempts, missed_sessions=missed)
    if target == today:
        if attempts >= passed:
            return Decision(False, "not_yet", target, attempts, missed_sessions=missed)
        return Decision(True, "scheduled", target, attempts + 1, send=True, missed_sessions=missed, kinds=report_kinds(target, cal))
    return Decision(True, "catch_up", target, attempts + 1, send=True, missed_sessions=missed, kinds=report_kinds(target, cal))


def scheduler_lease(store: JobStore, now: datetime, *, worker_id: str, ttl: float = 900) -> str:
    """One scheduler tick per hour bucket across processes."""
    local = now.astimezone(VN)
    return store.acquire(f"scheduler:{local:%Y-%m-%dT%H}", worker_id=worker_id, now=now.timestamp(), ttl=ttl)


@dataclass(frozen=True)
class TickResult:
    decision: Decision
    statuses: list[str]
    delivered: list[str]


def scheduled_tick(*, repo, owner, market, jobs: JobStore, deliveries, sender, cal: TradingCalendar, now: datetime, worker_id: str,
                   reminders: list[str] | tuple = (), market_for=lambda session: None) -> TickResult:
    """One scheduler wake-up: decide, run the due report kinds, then send queued reports if scheduled sending is on."""
    scheduler_lease(jobs, now, worker_id=worker_id)
    reports = list_reports(repo, owner)
    published = frozenset(date.fromisoformat(r["session_date"]) for r in reports if r["status"] == "published" and r["report_kind"] == "after_close")
    attempts = {date.fromisoformat(k): v for k, v in jobs.attempts().items()}
    decision = decide(now, cal, ReportState(published=published, attempts=attempts))
    statuses, delivered = [], []
    if not decision.run:
        if decision.reason == "already_published":
            # Published by hand (Tạo bản tin) before the slot: still send it, but only for the current session.
            delivered = _send_queued(repo, owner, deliveries, sender, session=decision.session_date, market_for=market_for)
        return TickResult(decision, statuses, delivered)
    jobs.count_attempt(decision.session_date.isoformat())
    for kind in decision.kinds:
        result = run_after_close(repo=repo, owner=owner, market=market, jobs=jobs, outbox=deliveries, session_date=decision.session_date,
                                 now=now, worker_id=worker_id, report_kind=kind, reminders=reminders)
        statuses.append(result.status)
    if decision.send:
        delivered = _send_queued(repo, owner, deliveries, sender, market_for=market_for)
    return TickResult(decision, statuses, delivered)


def _send_queued(repo, owner, deliveries, sender, *, session: date | None = None, market_for=lambda session: None) -> list[str]:
    """Send queued reports when scheduled sending is on; with session, only that session's reports."""
    settings, _ = current_settings(repo, owner)
    if not settings.scheduled_enabled or sender is None:
        return []
    delivered = []
    for report_id in deliveries.queued():
        report = get_report(repo, owner, report_id)
        if not report or (session is not None and report.get("session_date") != session.isoformat()):
            continue
        result = deliver(report, settings, sender, deliveries, market_for(report.get("session_date")))
        if result.status == "sent":
            deliveries.mark_processed(report_id)
            if result.parts_new:  # already sent elsewhere (e.g. from the app): off the queue, but not counted as delivered again
                delivered.append(report_id)
    return delivered
