"""Reference valuation of VNINDEX and VN30: today's P/E and P/B against their own five-year daily median.

Fair level of a method = index close × median multiple / current multiple, on the date of the latest multiple. Same
verdict rule as the ticker board (median of methods, ±threshold from Cài đặt). A method without enough data gives a
reason and no value; fewer than two values means no verdict.
"""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from .reference import Settings, _median

LABELS = {"pe_history": "P/E lịch sử", "pb_history": "P/B lịch sử"}
NAMES = {"VNINDEX": "VN-Index", "VN30": "VN30"}
WINDOW_YEARS, MIN_YEARS, MAX_AGE_DAYS = 5, 4, 10
_P2 = Decimal("0.01")

Points = list[tuple[datetime, float]]


def _years_before(day: date, years: int) -> date:
    return day.replace(year=day.year - years, day=28) if (day.month, day.day) == (2, 29) else day.replace(year=day.year - years)


def _vn(day: date) -> str:
    return day.strftime("%d/%m/%Y")


def _method(name: str, points: Points, closes: dict[date, Decimal], today: date) -> dict:
    out = {"method": name, "label": LABELS[name], "value": None, "reason": None, "inputs": {}}
    if not points:
        return {**out, "reason": "Chưa có số liệu"}
    latest_day = points[-1][0].date()
    if (today - latest_day).days > MAX_AGE_DAYS:
        return {**out, "reason": f"Số liệu mới nhất ngày {_vn(latest_day)}, cũ hơn {MAX_AGE_DAYS} ngày"}
    if points[0][0].date() > _years_before(latest_day, MIN_YEARS):
        return {**out, "reason": f"Cần lịch sử ít nhất {MIN_YEARS} năm"}
    close = closes.get(latest_day)
    if close is None:
        return {**out, "reason": f"Chưa có điểm chỉ số ngày {_vn(latest_day)}"}
    since = _years_before(latest_day, WINDOW_YEARS)
    window = [Decimal(str(v)) for t, v in points if t.date() > since]
    now, median = Decimal(str(points[-1][1])), _median(window)
    return {**out, "value": (close * median / now).quantize(_P2, ROUND_HALF_UP),
            "inputs": {"now": str(now.quantize(_P2, ROUND_HALF_UP)), "median": str(median.quantize(_P2, ROUND_HALF_UP)),
                       "since": since.isoformat(), "points": len(window)}}


def value_index(index: str, *, pe: Points, pb: Points, closes: Points, settings: Settings, today: date) -> dict:
    by_day = {t.date(): Decimal(str(v)) for t, v in closes}
    methods = [_method("pe_history", pe, by_day, today), _method("pb_history", pb, by_day, today)]
    latest = max((p[-1][0].date() for p in (pe, pb) if p), default=None)
    close = by_day.get(latest) if latest else None
    row = {"symbol": index, "name": NAMES.get(index, index), "as_of": latest.isoformat() if latest else None,
           "close": str(close.quantize(_P2, ROUND_HALF_UP)) if close is not None else None,
           "fair": None, "low": None, "high": None, "gap": None, "verdict": "insufficient", "reason": None, "methods": methods}
    values = [m["value"] for m in methods if m["value"] is not None]
    for m in methods:
        m["value"] = str(m["value"]) if m["value"] is not None else None
    if len(values) < 2:
        return {**row, "reason": "Ít hơn 2 phương án đủ dữ liệu"}
    fair = _median(values).quantize(_P2, ROUND_HALF_UP)
    gap = close / fair - 1
    verdict = "cheap" if gap <= -settings.threshold else "expensive" if gap >= settings.threshold else "fair"
    return {**row, "fair": str(fair), "low": str(min(values)), "high": str(max(values)),
            "gap": str(gap.quantize(Decimal("0.0001"), ROUND_HALF_UP)), "verdict": verdict}
