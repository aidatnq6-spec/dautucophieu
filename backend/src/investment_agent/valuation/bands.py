"""Dải phân vị: where this week's P/E or P/B stands within its own weekly history over 3 years, 5 years and the whole series.

Percentiles interpolate linearly between the two nearest sorted values (the common "type 7" rule). Rank = share of the
window's weeks at or below today's value. Mean, population standard deviation, z = (today − mean) / sd and skew (Fisher–
Pearson, population) describe the shape; when skew is large the mean ± sd band misleads and the percentiles should be read.

A window longer than the series is not drawn, and a window with fewer than MIN_WEEKS weeks that have a value gives a reason.
Weeks without a value (a loss, or no equity) are counted, never filled in.
"""

import math
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

MIN_WEEKS = 52
WINDOWS = (("3 năm", 3), ("5 năm", 5), ("Toàn bộ", None))
PCTS = (10, 20, 50, 70, 80, 95)
_Q2 = Decimal("0.01")


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else str(value.quantize(_Q2, ROUND_HALF_UP))


def percentile(sorted_values: list[Decimal], pct: int) -> Decimal:
    h = (len(sorted_values) - 1) * Decimal(pct) / 100
    lo = int(h)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (h - lo) * (sorted_values[hi] - sorted_values[lo])


def _years_before(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # 29 February
        return day.replace(year=day.year - years, day=28)


def _stats(sample: list[dict], current: Decimal | None) -> dict:
    values = [Decimal(p["value"]) for p in sample if p["value"] is not None]
    bases: dict[str, int] = {}
    for p in sample:
        if p["value"] is not None:
            bases[p["basis"]] = bases.get(p["basis"], 0) + 1
    out = {"weeks": len(values), "empty_weeks": len(sample) - len(values), "from": sample[0]["date"] if sample else None, "bases": bases,
           "p": None, "min": None, "max": None, "mean": None, "sd": None, "skew": None, "z": None, "rank": None, "reason": None}
    if len(values) < MIN_WEEKS:
        return {**out, "reason": f"Chỉ có {len(values)} tuần có số, cần ít nhất {MIN_WEEKS}"}
    xs = sorted(values)
    n = Decimal(len(xs))
    mean = sum(xs) / n
    m2 = sum((x - mean) ** 2 for x in xs) / n
    m3 = sum((x - mean) ** 3 for x in xs) / n
    sd = Decimal(str(math.sqrt(m2)))
    out.update(p={f"p{k}": _fmt(percentile(xs, k)) for k in PCTS}, min=_fmt(xs[0]), max=_fmt(xs[-1]), mean=_fmt(mean), sd=_fmt(sd),
               skew=_fmt(m3 / Decimal(str(math.sqrt(m2) ** 3))) if m2 > 0 else None)
    if current is not None:
        out["rank"] = int((Decimal(100) * sum(1 for x in xs if x <= current) / n).quantize(Decimal(1), ROUND_HALF_UP))
        out["z"] = _fmt((current - mean) / sd) if sd > 0 else None
    return out


def percentile_bands(points: list[dict]) -> dict:
    """Points as weekly_multiples gives them (date, value or None, basis), oldest first; today = the last point."""
    if not points:
        return {"current": None, "date": None, "windows": [], "reason": "Chưa có chuỗi theo tuần"}
    current = Decimal(points[-1]["value"]) if points[-1]["value"] is not None else None
    windows = []
    for label, years, sample, reason in window_samples(points):
        if reason is not None:
            windows.append({"label": label, "years": years, **_stats([], None), "weeks": 0, "reason": reason})
        else:
            windows.append({"label": label, "years": years, **_stats(sample, current)})
    return {"current": _fmt(current), "date": points[-1]["date"], "windows": windows, "reason": None}


def window_samples(points: list[dict]) -> list[tuple[str, int | None, list[dict], str | None]]:
    """Each window's weeks (label, years, points, reason); a window the series does not reach back to has a reason and no points."""
    end, first = date.fromisoformat(points[-1]["date"]), date.fromisoformat(points[0]["date"])
    out = []
    for label, years in WINDOWS:
        start = _years_before(end, years) if years else None
        if start is not None and first > start + timedelta(days=7):  # the series must reach back to the window's first week
            out.append((label, years, [], f"Chuỗi chỉ có từ {first.month:02d}/{first.year}, chưa đủ {years} năm"))
        else:
            out.append((label, years, [p for p in points if start is None or date.fromisoformat(p["date"]) > start], None))
    return out
