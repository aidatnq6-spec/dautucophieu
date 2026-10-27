"""Góp vốn đều: the owner's monthly contribution plan (`settings/contribution_plan`), checked against the ledger's deposits less
withdrawals, and a once-a-month Telegram reminder from the contribution day while the month is not yet met. Personal data."""

from datetime import date
from decimal import Decimal

from investment_agent.domain.contributions import contribution_status, reminder_due
from investment_agent.notifications.render import vnd
from investment_agent.services.records import LedgerBook, read_version

PLAN = ("settings", "contribution_plan")
REMINDED = ("settings", "contribution_reminded")


def cash_flows(repo, owner) -> list[tuple[date, Decimal]]:
    """Deposits (positive) and withdrawals (negative) in the effective ledger; raises RepositoryUnavailable."""
    events = LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events
    return [(e.effective_at, Decimal(e.amount) * (1 if e.type == "deposit" else -1)) for e in events if e.type in ("deposit", "withdrawal")]


def render_reminder(month: str, *, net: str, amount: str, streak: int) -> str:
    year, m = month.split("-")
    gap = Decimal(amount) - Decimal(net)
    lines = [f"Góp vốn đều — tháng {m}/{year} chưa đủ", f"Đã nộp vào sổ: {vnd(net)} / kế hoạch {vnd(amount)} (còn thiếu {vnd(format(gap, 'f'))})"]
    lines.append(f"Chuỗi góp đều hiện tại: {streak} tháng" if streak else "Chưa có chuỗi góp đều; tháng này là lúc bắt đầu.")
    lines.append("Khi đã chuyển tiền, ghi giao dịch \"Nộp tiền\" vào sổ để ứng dụng ghi nhận.")
    return "\n".join(lines)


def remind_run(repo, owner, *, today: date, send, request_id: str) -> dict:
    plan = read_version(repo, owner, *PLAN, None)
    if plan is None:
        return {"due": None, "sent": False}
    status = contribution_status(cash_flows(repo, owner), plan.payload, today=today)
    record = read_version(repo, owner, *REMINDED, None)
    due = reminder_due(status, today=today, reminded_month=record.payload.get("month") if record else None)
    if due is None:
        return {"due": None, "sent": False}
    current = status["months"][-1]
    previous_streak = status["streak"]
    if not send(render_reminder(due, net=current["net"], amount=plan.payload["amount"], streak=previous_streak)):
        return {"due": due, "sent": False}  # not recorded: the next run tries again
    repo.write(owner, *REMINDED, {"month": due}, expected_version=record.version if record else 0, request_id=request_id)
    return {"due": due, "sent": True}
