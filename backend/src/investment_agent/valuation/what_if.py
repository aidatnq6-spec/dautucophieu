"""Giá giả định: the P/E or P/B a price the owner types would give, where it stands in the ticker's weekly history, and what
happened twelve months after the earlier times the multiple fell to that level.

The multiple uses the latest week's denominator (trailing-four-quarter profit or latest equity, as the weekly series has it)
and today's share count: price × shares / denominator. Rank = share of each window's weeks at or below it.

Episodes (whole weekly series): an entry is the first week the multiple is at or below the level after being above it (or
without a value, e.g. a loss week); a new entry also needs a year since the previous one, so the twelve-month results do not
overlap; weeks already below when the series starts are not an entry, since when the multiple fell is unknown. The result is the week's adjusted close on the first week at least 365 days later (within 14 days, otherwise the
gap in prices leaves it unjudged); the fall is the lowest weekly close up to then against the entry close (0 if it never fell).
An episode without twelve months of prices yet is pending. A win rate and a median need at least MIN_EPISODES judged
episodes; fewer are listed, never turned into a rate. Weekly closes, so a fall within a week is not seen. This ticker only,
and it is still listed: the history of companies that did not recover is not in the sample.
"""

import statistics
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .bands import MIN_WEEKS, window_samples

MIN_EPISODES = 5
YEAR_DAYS, LATE_DAYS = 365, 14
_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")


def _r(value: Decimal | None, q: Decimal = _Q4) -> str | None:
    return None if value is None else str(value.quantize(q, ROUND_HALF_UP))


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def episodes(points: list[dict], *, level: Decimal) -> dict:
    days = [date.fromisoformat(p["date"]) for p in points]
    entries, below, last = [], True, None  # weeks already below when the series starts: when they fell is unknown, so no entry
    for i, p in enumerate(points):
        now_below = p["value"] is not None and Decimal(p["value"]) <= level
        if now_below and not below and (last is None or (days[i] - last).days >= YEAR_DAYS):
            entries.append(i)
            last = days[i]
        below = now_below
    rows = []
    for i in entries:
        entry_close, due = Decimal(points[i]["close"]), days[i] + timedelta(days=YEAR_DAYS)
        j = next((k for k in range(i + 1, len(points)) if days[k] >= due), None)
        row = {"entry": points[i]["date"], "multiple": _r(Decimal(points[i]["value"]), _Q2), "entry_close": points[i]["close"],
               "exit": None, "exit_close": None, "return": None, "drawdown": None}
        if j is not None and (days[j] - due).days <= LATE_DAYS:
            low = min(Decimal(points[k]["close"]) for k in range(i + 1, j + 1))
            exit_close = Decimal(points[j]["close"])
            row.update(exit=points[j]["date"], exit_close=points[j]["close"], **{"return": _r(exit_close / entry_close - 1)},
                       drawdown=_r(min(Decimal(0), low / entry_close - 1)))
        rows.append(row)
    judged = [r for r in rows if r["return"] is not None]
    returns = [Decimal(r["return"]) for r in judged]
    enough = len(judged) >= MIN_EPISODES
    return {"list": rows, "done": len(judged), "pending": len(rows) - len(judged), "wins": sum(1 for x in returns if x > 0),
            "win_rate": _r(Decimal(sum(1 for x in returns if x > 0)) / len(returns)) if enough else None,
            "median": _r(Decimal(statistics.median(returns))) if enough else None,
            "worst_return": _r(min(returns)) if returns else None,
            "worst_drawdown": _r(min(Decimal(r["drawdown"]) for r in judged)) if judged else None,
            "min_episodes": MIN_EPISODES}


def what_if(points: list[dict], *, shares: int, price: Decimal) -> dict:
    """Points of one weekly series (P/E or P/B), oldest first; the last is today."""
    if not points:
        return {"multiple": None, "windows": [], "episodes": None, "reason": "Chưa có chuỗi theo tuần"}
    latest = points[-1]
    denominator, close = Decimal(latest["denominator"]), Decimal(latest["close"])
    base = {"price": _plain(price), "close": latest["close"], "date": latest["date"], "change": _r(price / close - 1),
            "basis": latest["basis"], "period": latest["period"], "per_share": _plain((denominator / shares).quantize(Decimal(1), ROUND_HALF_UP))}
    if denominator <= 0:
        return {**base, "multiple": None, "windows": [], "episodes": None,
                "reason": "Mẫu số không dương (lỗ hoặc vốn chủ âm): không có bội số"}
    multiple = (price * shares / denominator).quantize(_Q2, ROUND_HALF_UP)
    windows = []
    for label, years, sample, reason in window_samples(points):
        values = [Decimal(p["value"]) for p in sample if p["value"] is not None]
        if reason is None and len(values) < MIN_WEEKS:
            reason = f"Chỉ có {len(values)} tuần có số, cần ít nhất {MIN_WEEKS}"
        windows.append({"label": label, "years": years, "weeks": len(values), "reason": reason,
                        "rank": None if reason else int((Decimal(100) * sum(1 for v in values if v <= multiple) / len(values)).quantize(Decimal(1), ROUND_HALF_UP))})
    return {**base, "multiple": str(multiple), "windows": windows, "episodes": episodes(points, level=multiple), "reason": None}
