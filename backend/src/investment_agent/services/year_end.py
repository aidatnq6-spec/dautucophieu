"""Việc cuối năm on Năm tài chính (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-nam-tai-chinh-design.md).

The app's checks are read from stored data (gather_facts, each one on its own so one unreadable part never stops the others); the
owner's ticks and the reminders already sent are kept in `settings/year_end_<year>`. The reminder is one part of Việc tài chính hôm
nay. Personal data; never sent to a model."""

from datetime import date, datetime, timedelta
from pathlib import Path

from investment_agent.domain.year_end import MANUAL, checklist_year, reminder_due, render_reminder, theses_fact, tower_fact, year_end_view
from investment_agent.services.records import read_version

DRILL_DAYS = 30


class YearEndError(ValueError):
    pass


def _record(year: int) -> tuple[str, str]:
    return ("settings", f"year_end_{year}")


def _state(repo, owner, year: int) -> tuple[dict, int]:
    rec = read_version(repo, owner, *_record(year), None)
    return (rec.payload, rec.version) if rec else ({"ticks": [], "reminded": []}, 0)


def _guard(read) -> tuple[bool | None, str]:
    try:
        return read()
    except Exception as exc:  # one check unreadable: said, the list still opens
        return None, f"không đọc được ({type(exc).__name__})"


def gather_facts(repo, owner, *, data_dir: Path | None, config_dir: Path, today: date, now: datetime, quotes: dict) -> dict:
    """The app's checks for the year ending: id → (done, detail)."""
    year = checklist_year(today) or today.year
    nxt = year + 1

    def theses():
        from investment_agent.services.theses import position_shares, read_theses
        return theses_fact(read_theses(repo, owner)[0], held=set(position_shares(repo, owner)), today=today)

    def tower():
        from investment_agent.services.equity_budget import budget_view
        return tower_fact(budget_view(repo, owner, quotes=quotes)[0].get("pyramid"))

    def calendar():
        have = (Path(config_dir) / f"trading-calendar-hose-{nxt}.json").is_file()
        return (True, f"đã có lịch {nxt}") if have else (False, f"chưa có lịch {nxt}; HOSE thường công bố cuối tháng 12")

    def drill():
        from investment_agent.services.system_health import _read_drill, _when
        if data_dir is None:
            return None, "không có thư mục dữ liệu trên máy này"
        last = _read_drill(Path(data_dir))
        if last is None:
            return False, "chưa diễn tập lần nào"
        at = _when(last["at"])
        if not last["ok"]:
            return False, f"lần gần nhất {at:%d/%m/%Y} không đạt"
        return (now - at <= timedelta(days=DRILL_DAYS)), f"lần gần nhất {at:%d/%m/%Y}"

    def goals():
        have = read_version(repo, owner, "settings", f"year_goals_{nxt}", None) is not None
        return (True, f"đã đặt mục tiêu {nxt}") if have else (False, f"chưa đặt mục tiêu {nxt}")

    return {k: _guard(f) for k, f in (("theses", theses), ("tower", tower), ("calendar", calendar), ("drill", drill), ("goals", goals))}


def view(repo, owner, *, today: date, facts: dict) -> dict:
    year = checklist_year(today)
    if year is None:
        start = date(today.year, 12, 1)
        return {"open": False, "opens_on": start.isoformat()}
    state, version = _state(repo, owner, year)
    return {"open": True, "version": version, **year_end_view(year, facts=facts, ticks=set(state["ticks"]))}


def tick(repo, owner, *, today: date, item: str, done: bool, expected_version: int, request_id: str, facts: dict) -> dict:
    year = checklist_year(today)
    if year is None:
        raise YearEndError("Danh sách Việc cuối năm chỉ mở từ 01/12 đến 31/01.")
    if item not in MANUAL:
        raise YearEndError("Việc này phần mềm tự kiểm, không đánh dấu tay.")
    state, _ = _state(repo, owner, year)
    ticks = (set(state["ticks"]) | {item}) if done else (set(state["ticks"]) - {item})
    repo.write(owner, *_record(year), {**state, "ticks": sorted(ticks)}, expected_version=expected_version, request_id=request_id)
    return view(repo, owner, today=today, facts=facts)


def remind_run(repo, owner, *, today: date, send, request_id: str, facts: dict) -> dict:
    """One note on or after 1/12, 20/12 and 5/1 while something is left; marked only once sent, so a failed send is tried again."""
    year = checklist_year(today)
    if year is None:
        return {"due": None, "sent": False}
    state, version = _state(repo, owner, year)
    due = reminder_due(today, reminded=state["reminded"])
    if due is None:
        return {"due": None, "sent": False}
    text = render_reminder(year_end_view(year, facts=facts, ticks=set(state["ticks"])))
    if text is None:
        return {"due": due, "sent": False, "left": 0}
    if not send(text):
        return {"due": due, "sent": False}
    repo.write(owner, *_record(year), {**state, "reminded": [*state["reminded"], due]}, expected_version=version, request_id=request_id)
    return {"due": due, "sent": True}


SNAPSHOTS = ("settings", "wealth_snapshots")


def read_snapshots(repo, owner) -> dict:
    """Month → {taken_on, total, layers: id → amount}: Tháp tài sản's totals only, the last day written in each month."""
    rec = read_version(repo, owner, *SNAPSHOTS, None)
    return rec.payload.get("months", {}) if rec else {}


def snapshot_run(repo, owner, *, pyramid: dict | None, today: date, request_id: str) -> dict:
    """Overwrites this month's snapshot once a day, so the month keeps its last day (spec: the year's start against its end from
    2027). No Tháp tài sản: nothing written, never a guessed figure."""
    month = f"{today:%Y-%m}"
    if not pyramid:
        return {"month": month, "written": False, "reason": "no_pyramid"}
    rec = read_version(repo, owner, *SNAPSHOTS, None)
    months = dict(rec.payload.get("months", {})) if rec else {}
    if months.get(month, {}).get("taken_on") == today.isoformat():
        return {"month": month, "written": False}
    months[month] = {"taken_on": today.isoformat(), "total": pyramid["total"],
                     "layers": {layer["id"]: layer["amount"] for layer in pyramid["layers"]}}
    repo.write(owner, *SNAPSHOTS, {"months": months}, expected_version=rec.version if rec else 0, request_id=request_id)
    return {"month": month, "written": True}


def year_review(repo, owner, *, data_dir: Path | None, year: int, today: date, quotes: dict) -> dict:
    """Tổng kết năm: each part read on its own; a part that cannot be read says so and the others still show."""
    from investment_agent.domain import year_review as yr
    from investment_agent.services.records import LedgerBook

    def events():
        return list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)

    def portfolio():
        from investment_agent.domain.time_weighted import performance
        from investment_agent.market.series import SeriesStore
        evs = events()
        if data_dir is None:
            return {"return": None, "note": "không có thư mục giá trên máy này"}
        store = SeriesStore(Path(data_dir) / "trend-sources")
        symbols = {e.security_id for e in evs if getattr(e, "security_id", None)}
        closes = {s: {t.date(): v * 1000 for t, v in store.read(f"{s}-1d")} for s in symbols}  # thousand đồng, as Hiệu suất reads them
        index = {t.date(): v for t, v in store.read("VNINDEX-1d")}
        return yr.year_portfolio(performance(evs, closes=closes, index=index, today=min(today, date(year, 12, 31))), year=year)

    def contributions():
        from investment_agent.domain.contributions import contribution_status
        from investment_agent.services.contributions import PLAN, cash_flows
        plan = read_version(repo, owner, *PLAN, None)
        if plan is None:
            return None
        status = contribution_status(cash_flows(repo, owner), plan.payload, today=today)
        return yr.year_contributions(status, amount=plan.payload["amount"], year=year)

    def cashflow():
        from investment_agent.services.cashflow import RECORD
        rec = read_version(repo, owner, *RECORD, None)
        return yr.year_cashflow(rec.payload if rec else None, year=year, today=today)

    def tower():
        from investment_agent.services.equity_budget import budget_view
        return yr.year_tower(read_snapshots(repo, owner), budget_view(repo, owner, quotes=quotes)[0].get("pyramid"), year=year)

    out = {"year": year, "as_of": min(today, date(year, 12, 31)).isoformat(), "running": today <= date(year, 12, 31)}
    for key, part in (("portfolio", portfolio), ("flows", lambda: yr.year_flows(events(), year=year)), ("contributions", contributions),
                      ("cashflow", cashflow), ("tower", tower)):
        try:
            out[key] = part()
        except Exception as exc:  # one part unreadable: named, the others still show
            out[key] = {"error": f"không đọc được ({type(exc).__name__})"}
    return out
