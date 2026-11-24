"""Lãi đã trả lại thị trường and Mục tiêu đã đủ tiền from the ledger and the stored closes; reminders in the Danh mục hôm nay note and
lines for Việc cần xem. Personal data, computed on the owner's machine, never sent to a model. Figures only, no advice."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from investment_agent.domain.giveback import giveback, giveback_alerts, goal_alerts, goal_status
from investment_agent.domain.models import ContractModel, UnsignedAmount
from investment_agent.market.series import SeriesStore
from investment_agent.notifications.render import _num, vnd
from investment_agent.services.journal import read_journal
from investment_agent.services.records import LedgerBook, portfolio_settings, read_version

GOALS = ("settings", "spend_goals")
ALERTS = ("settings", "giveback_alerts")
MAX_GOALS = 10
BASIS = {"value": "giá trị danh mục", "gain": "lãi chưa chốt của danh mục"}


class GoalClose(ContractModel):
    kind: Literal["done", "dropped"]
    on: date


class SpendGoal(ContractModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    name: str = Field(min_length=1, max_length=80, pattern=r"\S")
    amount: UnsignedAmount
    basis: Literal["value", "gain"]
    created_on: date
    closed: GoalClose | None = None

    @model_validator(mode="after")
    def _positive(self):
        if self.amount <= 0:
            raise ValueError("a goal needs an amount above zero")
        return self


class SpendGoals(ContractModel):
    goals: tuple[SpendGoal, ...] = Field(default=(), max_length=MAX_GOALS)

    @model_validator(mode="after")
    def _unique(self):
        if len({g.id for g in self.goals}) != len(self.goals):
            raise ValueError("goal ids must be unique")
        return self


def read_goals(repo, owner) -> tuple[list[dict], int]:
    record = read_version(repo, owner, *GOALS, None)
    if not record:
        return [], 0
    return list(SpendGoals.model_validate(record.payload).model_dump(mode="json")["goals"]), record.version


def write_goals(repo, owner, goals: list[dict], *, expected_version: int, request_id: str):
    payload = SpendGoals.model_validate({"goals": goals}).model_dump(mode="json")
    return repo.write(owner, *GOALS, payload, expected_version=expected_version, request_id=request_id)


def _figures(repo, owner, data_dir: Path, today: date) -> dict:
    """Raises RepositoryUnavailable."""
    events = list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)
    store = SeriesStore(Path(data_dir) / "trend-sources")
    symbols = {e.security_id for e in events if getattr(e, "security_id", None)} | {p.security_id for e in events for p in getattr(e, "positions", ())}
    closes = {s: [(t.date(), v) for t, v in store.read(f"{s}-1d")] for s in symbols}
    return giveback(events, closes=closes, today=today)


def _with_status(goals: list[dict], days: list[dict]) -> list[dict]:
    return [{**g, "status": goal_status(g, days)} for g in goals]


def giveback_for(repo, owner, data_dir: Path, *, today: date) -> dict:
    """The page: holdings, the portfolio, the owner's thresholds and goals with their state. Raises RepositoryUnavailable."""
    out = _figures(repo, owner, data_dir, today)
    settings = portfolio_settings(repo, owner)[0]
    goals, version = read_goals(repo, owner)
    min_gain, share = settings.giveback_min_gain, settings.giveback_share
    return {**out, "thresholds": {"min_gain": None if min_gain is None else format(min_gain, "f"), "share": None if share is None else format(share, "f")},
            "goals": _with_status(goals, out["portfolio"]["days"]), "goals_version": version, "as_of": today.isoformat()}


def _dmy(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


def _pct(ratio: str, sign: bool = False) -> str:
    return _num(Decimal(ratio) * 100, 1, sign=sign) + "%"


def _goal_head(goal: dict) -> str:
    return f"{goal['name']} ({vnd(goal['amount'])}, theo {BASIS[goal['basis']]})"


def render_note(rows: list[dict], goals: list[dict], *, reasons: dict[str, str]) -> str:
    """Plain text: the peak, today and what went back, with the dates; goals covered or short again. No advice."""
    lines = []
    if rows:
        lines.append("Lãi đã trả lại thị trường — chạm ngưỡng bạn đặt")
        for r in rows:
            p, n = r["peak"], r["now"]
            lines += ["", f"{r['symbol']}: lãi cao nhất {vnd(p['gain'])} ({_pct(p['ratio'], True)}) ngày {_dmy(p['on'])}; "
                          f"ngày {_dmy(n['on'])} còn {vnd(n['gain'])} ({_pct(n['ratio'], True)})",
                      f"Đã trả lại {vnd(r['given_back'])}, bằng {_pct(r['share'])} lãi cao nhất."]
            if reason := reasons.get(r["symbol"]):
                lines.append(f"Lý do bạn đã ghi: {reason}")
    if goals:
        lines += ["", "Mục tiêu đã đủ tiền"] if lines else ["Mục tiêu đã đủ tiền"]
        for a in goals:
            s = a["status"]
            if a["kind"] == "enough":
                lines.append(f"{_goal_head(a['goal'])}: đã đủ từ {_dmy(s['since'])}.")
            else:
                last = s.get("last") or {}
                was = f"đã đủ từ {_dmy(last['from'])} đến {_dmy(last['to'])}, " if last else ""
                lines.append(f"{_goal_head(a['goal'])}: {was}nay còn thiếu {vnd(s['short'])}.")
    lines += ["", "Chỉ là số đã xảy ra, theo ngưỡng và mục tiêu bạn tự đặt."]
    return "\n".join(lines)


def giveback_run(repo, owner, data_dir: Path, *, send, request_id: str, today: date) -> dict:
    """Reminds once per crossing; what was not delivered is tried again next run."""
    out = _figures(repo, owner, data_dir, today)
    settings = portfolio_settings(repo, owner)[0]
    goals, _ = read_goals(repo, owner)
    record = read_version(repo, owner, *ALERTS, None)
    before = record.payload if record else {"alerted": [], "goals": {}}
    alerted_before, states_before = set(before.get("alerted", [])), dict(before.get("goals", {}))
    rows, alerted = giveback_alerts(out["rows"], min_gain=settings.giveback_min_gain, share=settings.giveback_share, alerted=alerted_before)
    pairs = [(g, goal_status(g, out["portfolio"]["days"])) for g in goals]
    reached, states = goal_alerts(pairs, states=states_before)
    sent = False
    if rows or reached:
        entries, _ = read_journal(repo, owner)
        reasons = {e.symbol: e.reason for e in sorted(entries, key=lambda e: e.created_on) if e.reason}
        sent = bool(send(render_note(rows, reached, reasons=reasons)))
        if not sent:  # not delivered: the same crossings are told next run
            alerted -= {f"{r['symbol']}@{r['since']}" for r in rows}
            for a in reached:
                gid = a["goal"]["id"]
                if gid in states_before:
                    states[gid] = states_before[gid]
                else:
                    states.pop(gid, None)
    payload = {"alerted": sorted(alerted), "goals": states}
    if payload != {"alerted": sorted(alerted_before), "goals": states_before}:
        repo.write(owner, *ALERTS, payload, expected_version=record.version if record else 0, request_id=request_id)
    return {"holdings": len(rows), "goals": len(reached), "sent": sent}


def attention_lines(repo, owner, data_dir: Path, *, today: date) -> list[tuple[str, str | None, str]]:
    """(kind, symbol, text) for Việc cần xem: holdings past both thresholds now, open goals covered now."""
    out = _figures(repo, owner, data_dir, today)
    settings = portfolio_settings(repo, owner)[0]
    rows, _ = giveback_alerts(out["rows"], min_gain=settings.giveback_min_gain, share=settings.giveback_share, alerted=set())
    lines = [("giveback", r["symbol"], f"{r['symbol']}: đã trả lại {_pct(r['share'])} lãi cao nhất ({vnd(r['peak']['gain'])} ngày "
                                       f"{_dmy(r['peak']['on'])}), lãi hôm nay {vnd(r['now']['gain'])}.") for r in rows]
    for g in read_goals(repo, owner)[0]:
        s = goal_status(g, out["portfolio"]["days"])
        if g.get("closed") or not s["enough"]:
            continue
        days = f" ({s['days']} ngày)" if s["days"] else ""
        lines.append(("goal", None, f"Mục tiêu «{g['name']}» đã đủ tiền từ {_dmy(s['since'])}{days}, theo {BASIS[g['basis']]}."))
    return lines
