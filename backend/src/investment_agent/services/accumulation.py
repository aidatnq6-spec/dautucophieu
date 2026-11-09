"""Kế hoạch tích sản (`settings/accumulation`): the view, the lines for Việc cần xem and the monthly Telegram note, once per plan and month from its day while the month is not met.
Personal data; never sent to a model."""

from datetime import date
from decimal import Decimal

from investment_agent.domain.accumulation import Accumulation, Plan, book_targets, due_plans, plan_status
from investment_agent.domain.deposit_book import DepositBook
from investment_agent.notifications.render import vnd
from investment_agent.services.deposit_book import read_book
from investment_agent.services.records import read_version

RECORD = ("settings", "accumulation")
REMINDED = ("settings", "accumulation_reminded")
NO_QUOTES = {"gold": {}, "funds": {}}


def read_data(repo, owner) -> tuple[Accumulation, int]:
    stored = read_version(repo, owner, *RECORD, None)
    return (Accumulation.model_validate(stored.payload), stored.version) if stored else (Accumulation(), 0)


def accumulation_view(repo, owner, *, quotes: dict, today: date) -> dict:
    data, version = read_data(repo, owner)
    book = read_book(repo, owner)[0]
    return {"version": version, "data": data.model_dump(mode="json"), "book_exists": book is not None,
            "plans": [{**plan_status(p, data.buys, quotes, today=today), "book_rows": book_targets(book or DepositBook(), p)} for p in data.plans],
            "gold_kinds": list((quotes["gold"].get("kinds") or {})), "gold_source": quotes["gold"].get("source"), "nav_source": "Fmarket" if quotes["funds"] else None}


def _progress(plan: Plan, month: dict) -> str:
    if plan.asset == "gold":
        chi = format(plan.chi.normalize(), "f").replace(".", ",")
        return f"đã mua {month['got'].replace('.', ',')} / {chi} chỉ"
    return f"đã mua {vnd(month['got'])} / {vnd(format(plan.amount, 'f'))}"


def _label(key: str) -> str:
    return f"{key[5:]}/{key[:4]}"


def due_lines(repo, owner, *, today: date, quotes: dict = NO_QUOTES) -> list[str]:
    return [f"Tích sản · {p.name}: đến kỳ tháng {_label(m['month'])}, {_progress(p, m)}" for p, m in due_plans(read_data(repo, owner)[0], quotes, today=today)]


def remind_run(repo, owner, *, today: date, send, request_id: str) -> dict:
    record = read_version(repo, owner, *REMINDED, None)
    marks = dict(record.payload.get("marks", {})) if record else {}
    key = today.strftime("%Y-%m")
    due = [(p, m) for p, m in due_plans(read_data(repo, owner)[0], NO_QUOTES, today=today) if marks.get(p.id) != key]
    if not due:
        return {"due": 0, "sent": False}
    lines = [f"Kế hoạch tích sản: đến kỳ tháng {_label(key)}", *(f"• {p.name}: {_progress(p, m)}" for p, m in due), "Khi đã mua, ghi lần mua ở Hồ sơ & rủi ro để ứng dụng ghi nhận. Không phải khuyến nghị."]
    if not send("\n".join(lines)):
        return {"due": len(due), "sent": False}  # not recorded: the next run tries again
    repo.write(owner, *REMINDED, {"marks": marks | {p.id: key for p, _ in due}}, expected_version=record.version if record else 0, request_id=request_id)
    return {"due": len(due), "sent": True}
