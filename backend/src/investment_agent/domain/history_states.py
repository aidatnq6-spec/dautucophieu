"""Trạng thái vĩ mô 2×2 for Thống kê lịch sử (owner, 21/11/2026): yes/no conditions, each known on a day only once its figure was out,
and VN-Index some sessions later in the four combinations of two of them.

When a figure counts as known (no look-ahead):
- Vietnam's monthly CPI, industrial production and exports (World Bank, dated at the month's end): from the 10th of the next month,
  the statistics office's release day.
- The month's average USD/VND: from the 1st of the next month.
- FRED's daily oil, broad dollar and US 10-year yield: from the next day. VN-Index P/E: the same day.
A session takes each condition's latest state known on it, if not older than 130 days (monthly) or 10 days (daily)."""

from __future__ import annotations

from bisect import bisect_right
from datetime import date, timedelta
from decimal import Decimal

from .history_stats import YEARS_5, forward_dips, forward_returns, group_summary

MONTHLY_LAG = timedelta(days=10)
QUARTER = timedelta(days=91)
# a month's figure stands for 130 days: the World Bank runs about four months behind (July's, known on 10 August, still the latest
# in November); a daily figure for 10 days
STALE = {"monthly": timedelta(days=130), "daily": timedelta(days=10)}

CONDITIONS = {
    "cpi_up": {"label": "Lạm phát (CPI) tăng so với 3 tháng trước", "series": "wb_vn_cpi_yoy", "kind": "monthly"},
    "fx_up": {"label": "Tỷ giá USD/VND tăng hơn {fx} trong 3 tháng", "series": "wb_vn_usdvnd", "kind": "monthly"},
    "iip_up": {"label": "Sản xuất công nghiệp tăng nhanh hơn trung bình 12 tháng", "series": "wb_vn_iip", "kind": "monthly"},
    "exports_up": {"label": "Xuất khẩu 3 tháng tăng so cùng kỳ", "series": "wb_vn_exports", "kind": "monthly"},
    "oil_up": {"label": "Giá dầu tăng trong 3 tháng", "series": "factor_oil", "kind": "daily"},
    "usd_up": {"label": "USD rộng mạnh lên trong 3 tháng", "series": "factor_usd", "kind": "daily"},
    "us10y_up": {"label": "Lợi suất Mỹ 10 năm tăng trong 3 tháng", "series": "us10y", "kind": "daily"},
    "pe_high": {"label": "P/E VN-Index trên trung vị 5 năm", "series": "vnindex_pe", "kind": "daily"},
}

Points = list[tuple[date, Decimal]]


def _monthly(key: str, pts: Points, fx: Decimal) -> list[tuple[date, bool]]:
    out = []
    for i, (d, v) in enumerate(pts):
        known = d + (timedelta(days=1) if key == "fx_up" else MONTHLY_LAG)
        if key in ("cpi_up", "fx_up") and i >= 3:
            out.append((known, v > pts[i - 3][1] if key == "cpi_up" else (pts[i - 3][1] and v / pts[i - 3][1] - 1 > fx)))
        elif key == "exports_up" and i >= 14:
            now, before = sum(p[1] for p in pts[i - 2:i + 1]), sum(p[1] for p in pts[i - 14:i - 11])
            if before:
                out.append((known, now / before - 1 > 0))
        elif key == "iip_up" and i >= 24:
            yoy = lambda j: pts[j][1] / pts[j - 12][1] - 1 if pts[j - 12][1] else None  # noqa: E731
            history = [yoy(j) for j in range(i - 12, i)]
            if yoy(i) is not None and all(h is not None for h in history):
                out.append((known, yoy(i) > sum(history) / 12))
    return [(d, bool(s)) for d, s in out]


def _daily_change(pts: Points) -> list[tuple[date, bool]]:
    days, out = [d for d, _ in pts], []
    for d, v in pts:
        j = bisect_right(days, d - QUARTER) - 1
        if j >= 0:
            out.append((d + timedelta(days=1), v > pts[j][1]))
    return out


def _pe_high(pts: Points) -> list[tuple[date, bool]]:
    out = []
    for i, (d, v) in enumerate(pts):
        window = sorted(x for e, x in pts[:i + 1] if e > d - YEARS_5)
        if len(window) >= 250:
            out.append((d, v > window[len(window) // 2]))
    return out


def condition_days(key: str, series: dict[str, Points], *, fx: Decimal) -> list[tuple[date, bool]]:
    """(the day the state became known, the state), oldest first."""
    spec = CONDITIONS[key]
    pts = series.get(spec["series"]) or []
    if key == "pe_high":
        return _pe_high(pts)
    if spec["kind"] == "monthly":
        return _monthly(key, pts, fx)
    return _daily_change(pts)


def _on_sessions(known: list[tuple[date, bool]], sessions: list[date], kind: str) -> dict[date, bool]:
    days, out = [d for d, _ in known], {}
    for s in sessions:
        i = bisect_right(days, s) - 1
        if i >= 0 and s - days[i] <= STALE[kind]:
            out[s] = known[i][1]
    return out


def states_table(a: list[tuple[date, bool]], b: list[tuple[date, bool]], closes: Points, *, h: int,
                 kinds: tuple[str, str] = ("daily", "daily")) -> dict:
    sessions = [d for d, _ in closes]
    index = {d: i for i, d in enumerate(sessions)}
    returns, dips = forward_returns(closes, h), forward_dips(closes, h)
    sa, sb = _on_sessions(a, sessions, kinds[0]), _on_sessions(b, sessions, kinds[1])
    both = [d for d in sessions if d in sa and d in sb]
    rows = []
    for x, y in ((True, True), (True, False), (False, True), (False, False)):
        cell = [d for d in both if sa[d] is x and sb[d] is y]
        mine = set(cell)
        rows.append({"a": x, "b": y, **group_summary(cell, returns, index, h=h, dips=dips, rest=[d for d in both if d not in mine])})
    runs, start = [], None
    for d in both:  # the stretches where both held, for the chart
        if sa[d] and sb[d]:
            start = start or d
            end = d
        elif start:
            runs.append([start.isoformat(), end.isoformat()])
            start = None
    if start:
        runs.append([start.isoformat(), end.isoformat()])
    last = both[-1] if both and sessions and both[-1] == sessions[-1] else None  # "today" only when both are known on the latest session
    return {"h": h, "rows": rows, "all": group_summary(both, returns, index, h=h, dips=dips), "today": {"a": sa[last], "b": sb[last]} if last else None,
            "from": both[0].isoformat() if both else None, "runs": runs}
