"""Mục tiêu năm (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-nam-tai-chinh-design.md).

Up to three goals the owner sets for a year, each may be left out: money put in over the year, the savings rate, total assets at the
year's end. Each is set against an even pace through the year (the share of the year's days gone), which is a comparison, never a
forecast. Personal data; never sent to a model."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

BEHIND = Decimal("0.10")  # more than 10 points under the even pace: one line in Việc tài chính hôm nay at the start of the month
Q4 = Decimal("0.0001")


class GoalError(ValueError):
    pass


def _q(v: Decimal, q: Decimal = Q4) -> str:
    return format(v.quantize(q, ROUND_HALF_UP), "f")


def validate_goals(raw: dict) -> dict:
    """contribution and total_assets: whole đồng above 0; savings_rate: a share above 0 and below 1. At least one."""
    out = {}
    for key in ("contribution", "total_assets"):
        if raw.get(key) in (None, ""):
            continue
        try:
            v = Decimal(str(raw[key]))
        except InvalidOperation:
            raise GoalError("Số tiền phải là số đồng.") from None
        if not v.is_finite() or v <= 0 or v != v.to_integral_value():
            raise GoalError("Số tiền phải là số đồng lớn hơn 0.")
        out[key] = format(v, "f")
    if raw.get("savings_rate") not in (None, ""):
        try:
            r = Decimal(str(raw["savings_rate"]))
        except InvalidOperation:
            raise GoalError("Tỷ lệ tiết kiệm phải là số.") from None
        if not r.is_finite() or not 0 < r < 1:
            raise GoalError("Tỷ lệ tiết kiệm từ trên 0% đến dưới 100%.")
        out["savings_rate"] = format(r, "f")
    if not out:
        raise GoalError("Đặt ít nhất một mục tiêu.")
    return out


def pace(year: int, today: date) -> Decimal:
    """The share of the year's days gone by today (0 before the year, 1 after it)."""
    start, end = date(year, 1, 1), date(year, 12, 31)
    if today < start:
        return Decimal(0)
    if today >= end:
        return Decimal(1)
    return Decimal((today - start).days + 1) / Decimal((end - start).days + 1)


def goals_progress(goals: dict, *, year: int, today: date, put_in: str | None, savings_rate: str | None, total_now: str | None,
                   total_start: str | None) -> dict:
    """Each goal set: where it stands, the even pace and whether it is more than 10 points behind. A figure the app does not have
    leaves its goal without a reading (said, not guessed)."""
    p = pace(year, today)
    rows = []
    if "contribution" in goals:
        goal = Decimal(goals["contribution"])
        got = Decimal(put_in) if put_in is not None else None
        share = got / goal if got is not None else None
        rows.append({"id": "contribution", "goal": goals["contribution"], "now": put_in, "share": _q(share) if share is not None else None,
                     "pace": _q(p), "behind": share is not None and p - share > BEHIND})
    if "savings_rate" in goals:
        rows.append({"id": "savings_rate", "goal": goals["savings_rate"], "now": savings_rate, "share": None, "pace": None,
                     "behind": savings_rate is not None and Decimal(savings_rate) < Decimal(goals["savings_rate"])})
    if "total_assets" in goals:
        goal = Decimal(goals["total_assets"])
        share = None
        if total_now is not None and total_start is not None and goal != Decimal(total_start):
            share = (Decimal(total_now) - Decimal(total_start)) / (goal - Decimal(total_start))  # the way from the start to the goal
        rows.append({"id": "total_assets", "goal": goals["total_assets"], "now": total_now, "start": total_start,
                     "share": _q(share) if share is not None else None, "pace": _q(p) if share is not None else None,
                     "behind": share is not None and p - share > BEHIND})
    return {"year": year, "pace": _q(p), "rows": rows}
