"""Góp vốn đều: a fixed monthly contribution, read from the ledger's deposits less withdrawals in each month — "boring, repeated every
month" (VWA). It counts and reminds; it never moves money or says what to buy."""

from datetime import date
from decimal import Decimal


def _months(start: str, today: date) -> list[str]:
    y, m = map(int, start.split("-"))
    out = []
    while (y, m) <= (today.year, today.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def contribution_status(cash_flows: list[tuple[date, Decimal]], plan: dict, *, today: date) -> dict:
    """cash_flows: (date, amount) with deposits positive and withdrawals negative. plan: amount, day (1–28), start ("YYYY-MM").

    Each month from the start is met, short, none, or pending (the current month before its day, not yet met)."""
    amount, day = Decimal(plan["amount"]), int(plan["day"])
    net: dict[str, Decimal] = {}
    for when, value in cash_flows:
        key = f"{when.year:04d}-{when.month:02d}"
        net[key] = net.get(key, Decimal(0)) + value
    months = []
    for key in _months(plan["start"], today):
        got = net.get(key, Decimal(0))
        current = key == f"{today.year:04d}-{today.month:02d}"
        if got >= amount:
            status = "met"
        elif current and today.day < day:
            status = "pending"
        else:
            status = "short" if got > 0 else "none"
        months.append({"month": key, "net": format(got, "f"), "status": status,
                       "short_by": format(amount - got, "f") if status == "short" else None})
    due = [m for m in months if m["status"] != "pending"]
    streak = 0
    for m in reversed(due):
        if m["status"] != "met":
            break
        streak += 1
    return {"months": months, "streak": streak, "planned": format(amount * len(due), "f"),
            "contributed": format(sum((Decimal(m["net"]) for m in due), Decimal(0)), "f")}


def reminder_due(status: dict, *, today: date, reminded_month: str | None) -> str | None:
    """The current month when it is due (on or after the day), not yet met, and not reminded this month; else None."""
    if not status["months"]:
        return None
    current = status["months"][-1]
    key = f"{today.year:04d}-{today.month:02d}"
    if current["month"] != key or current["status"] in ("met", "pending") or reminded_month == key:
        return None
    return key
