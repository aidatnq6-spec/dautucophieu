"""Đáy nhịp và kênh tăng: MACD base zones and the rising channels drawn through them, on weekly, daily or hourly bars, on a
linear price scale.

Rules (no hand-picked points, nothing known before it happened):
- Bars: weekly ones from daily ones (keyed by the week's Monday: highest high, lowest low, last close); daily and hourly ones as the
  chart has them (hourly keys are Hà Nội wall-clock seconds). Rows with closes only (the Vĩ mô series) use the close for all three.
  The bar still running (this week, today in Hà Nội or UTC, this hour) is shown but never used.
- MACD 12/26/9 on the closes, as on the Xu hướng board. A base zone runs from a bearish cross (MACD under its signal) to the next
  bullish cross; its low is the lowest low in between. The zone drawn starts two bars before the low (not before the bearish cross)
  and ends at the bullish cross. A base is known only from its bullish cross.
- Point 0 = the lowest base low within the owner's lookback (years for weeks, months for days, weeks for hours). Point 2 = the next
  base, point 1 = the highest high between.
- Channels = edges of the lower convex hull through the bases from point 0, measured in bars (as the chart draws a straight line,
  so gaps for weekends, nights and holidays do not bend it): each base joins at the flattest point of its zone as seen from the
  previous joining point; a point on or above the line to the next one is dropped, so each later channel is steeper: basic →
  tăng tốc → final. Upper line: parallel through the highest high between the two joining points; the dotted line twice that width.
- Values at the last finished bar only; the lines are not drawn into the future.
- A break = the first finished bar whose close is under the final channel in force at that bar (built only from bases confirmed by
  then). Not a recommendation.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from .indicators import MIN_MACD_BARS, macd

_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")
VN = timezone(timedelta(hours=7))
WORDS = {"W": ("tuần", "năm"), "D": ("ngày", "tháng"), "H": ("1 giờ", "tuần")}


def _q(value: Decimal, q: Decimal = _Q2) -> str:
    return str(value.quantize(q, ROUND_HALF_UP))


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _ohlc(b: dict) -> tuple[Decimal, Decimal, Decimal]:
    c = Decimal(str(b["c"]))
    return Decimal(str(b.get("h", c))), Decimal(str(b.get("l", c))), c


def frame_bars(raw: list[dict], frame: str) -> list[dict]:
    if frame != "W":
        out = []
        for b in raw:
            h, low, c = _ohlc(b)
            out.append({"t": int(b["t"]) if frame == "H" else str(b["t"])[:10], "h": h, "l": low, "c": c})
        return out
    weeks: dict[date, dict] = {}
    for b in raw:
        h, low, c = _ohlc(b)
        key = _monday(date.fromisoformat(str(b["t"])[:10]))
        w = weeks.get(key)
        weeks[key] = {"t": key.isoformat(), "h": h, "l": low, "c": c} if w is None else {**w, "h": max(w["h"], h), "l": min(w["l"], low), "c": c}
    return [weeks[k] for k in sorted(weeks)]


def when(t, frame: str) -> datetime:
    """A bar's start as a naive Hà Nội wall-clock time."""
    return datetime.fromtimestamp(t, timezone.utc).replace(tzinfo=None) if frame == "H" else datetime.fromisoformat(str(t)[:10])


def running(t, frame: str, now: datetime) -> bool:
    local = now.astimezone(VN)
    if frame == "W":
        return date.fromisoformat(t) == _monday(local.date())
    if frame == "D":
        return date.fromisoformat(t) in (local.date(), now.astimezone(timezone.utc).date())  # Coinbase's day closes at 07:00 here
    start = when(t, "H")
    return start <= local.replace(tzinfo=None) < start + timedelta(hours=1)


def _months_before(dt: datetime, months: int) -> datetime:
    y, m = divmod(dt.year * 12 + dt.month - 1 - months, 12)
    for day in (dt.day, 30, 29, 28):
        try:
            return dt.replace(year=y, month=m + 1, day=day)
        except ValueError:
            continue
    raise ValueError("no such day")


def cutoff(last: datetime, frame: str, n: int) -> datetime:
    if frame == "W":
        return _months_before(last, 12 * n)
    if frame == "D":
        return _months_before(last, n)
    return last - timedelta(weeks=n)


def find_bases(bars: list[dict], line: list, signal: list) -> list[dict]:
    diff = [None if a is None or s is None else a - s for a, s in zip(line, signal)]
    out, start = [], None
    for i in range(1, len(bars)):
        if diff[i] is None or diff[i - 1] is None:
            continue
        if diff[i] <= 0 < diff[i - 1]:
            start = i
        elif diff[i] > 0 >= diff[i - 1] and start is not None:
            low_i = min(range(start, i + 1), key=lambda k: (bars[k]["l"], k))
            first = max(start, low_i - 2)
            out.append({"cross": i, "low_i": low_i, "low": bars[low_i]["l"], "zone_from": first, "zone_to": i,
                        "zone": [(k, bars[k]["l"]) for k in range(first, i + 1)]})
            start = None
    return out


def point_zero(bases: list[dict], bars: list[dict], *, frame: str, since: datetime) -> int | None:
    inside = [i for i, b in enumerate(bases) if when(bars[b["low_i"]]["t"], frame) >= since]
    return min(inside, key=lambda i: (bases[i]["low"], bases[i]["low_i"])) if inside else None


def _slope(a: tuple, b: tuple) -> Decimal:
    return (b[1] - a[1]) / (b[0] - a[0])


def line_at(a: tuple, b: tuple, i: int) -> Decimal:
    return a[1] + _slope(a, b) * (i - a[0])


def hull(chain: list[dict]) -> list[tuple[int, Decimal]]:
    """Joining points (bar index, price) of the lower convex hull from point 0's low, each later base at its flattest point."""
    pts = [(chain[0]["low_i"], chain[0]["low"])]
    for b in chain[1:]:
        while True:
            zone = [p for p in b["zone"] if p[0] > pts[-1][0]]
            if not zone:
                break
            cand = min(zone, key=lambda p: (_slope(pts[-1], p), p[0]))
            if len(pts) >= 2 and _slope(pts[-1], cand) <= _slope(pts[-2], pts[-1]):  # not steeper: no acceleration, one channel
                pts.pop()
                continue
            pts.append(cand)
            break
    return pts


def _state(close: Decimal, lower: Decimal, upper: Decimal) -> str:
    return "below" if close < lower else "above" if close > upper else "inside"


def channels(raw: list[dict], *, frame: str, now: datetime, n: int) -> dict:
    word, unit = WORDS[frame]
    bars = frame_bars(raw, frame)
    empty = {"frame": frame, "n": n, "bases": [], "zero": None, "points": {}, "channels": [], "status": None, "breaks": [], "in_progress": None,
             "last_bar": None, "bars": len(bars)}
    if not bars:
        return {**empty, "reason": "Chưa có dữ liệu giá"}
    if running(bars[-1]["t"], frame, now):
        live = bars.pop()
        empty["in_progress"] = {"t": live["t"], "c": _plain(live["c"])}
    empty["bars"] = len(bars)
    if len(bars) < MIN_MACD_BARS:
        return {**empty, "reason": f"Chỉ có {len(bars)} nến {word}, cần ít nhất {MIN_MACD_BARS} nến để có MACD"}
    last = len(bars) - 1
    empty["last_bar"] = bars[last]["t"]

    def t(i):
        return bars[i]["t"]

    def price(i, p):
        return {"date": t(i), "price": _plain(p)}

    line, signal = macd([float(b["c"]) for b in bars])
    since = cutoff(when(t(last), frame), frame, n)
    bases = [b for b in find_bases(bars, line, signal) if when(t(b["low_i"]), frame) >= since]
    zero = point_zero(bases, bars, frame=frame, since=since)
    listed = [{"cross": t(b["cross"]), "low_date": t(b["low_i"]), "low": _plain(b["low"]), "zone_from": t(b["zone_from"]), "zone_to": t(b["zone_to"]),
               "vs_prev": None if i == 0 else "higher" if b["low"] > bases[i - 1]["low"] else "lower"} for i, b in enumerate(bases)]
    if zero is None:
        return {**empty, "bases": listed, "reason": f"Không có đáy vùng MACD nào trong {n} {unit}"}
    chain = bases[zero:]
    points = {"0": price(chain[0]["low_i"], chain[0]["low"])}
    if len(chain) > 1:
        two = chain[1]
        between = range(chain[0]["low_i"] + 1, two["low_i"])
        if between:
            one = max(between, key=lambda i: (bars[i]["h"], i))
            points["1"] = price(one, bars[one]["h"])
        points["2"] = price(two["low_i"], two["low"])
    pts = hull(chain)
    edges = list(zip(pts, pts[1:]))
    kinds = ["final"] if len(edges) == 1 else ["basic"] + [f"accel{k}" for k in range(1, len(edges) - 1)] + ["final"]
    out, widths = [], []
    for kind, (a, b) in zip(kinds, edges):
        top = max(range(a[0], b[0] + 1), key=lambda i: (bars[i]["h"], i))
        width = bars[top]["h"] - line_at(a, b, top)
        lower = line_at(a, b, last)
        widths.append(width)
        out.append({"kind": kind, "from": price(*a), "to": price(*b), "slope": _q(_slope(a, b), _Q4), "top": price(top, bars[top]["h"]),
                    "lower_now": _q(lower), "upper_now": _q(lower + width), "double_now": _q(lower + 2 * width)})

    # Breaks: each finished bar against the final channel in force then (bases confirmed by that bar only).
    breaks, was_below, cache = [], False, {}
    for i in range(len(bars)):
        known = sum(1 for b in chain if b["cross"] <= i)  # bases are in time order, so the count names the known ones
        if known < 2:
            continue
        if known not in cache:
            cache[known] = hull(chain[:known])
        hp = cache[known]
        if len(hp) < 2 or i <= hp[-1][0]:
            was_below = False
            continue
        lower = line_at(hp[-2], hp[-1], i)
        below = bars[i]["c"] < lower
        if below and not was_below:
            breaks.append({"date": t(i), "close": _plain(bars[i]["c"]), "lower": _q(lower), "from": price(*hp[-2]), "to": price(*hp[-1])})
        was_below = below

    status = None
    if out:
        (a, b), width = edges[-1], widths[-1]

        def at(i):
            lo = line_at(a, b, i)
            return _state(bars[i]["c"], lo, lo + width)
        state, start = at(last), last
        while start - 1 > b[0] and at(start - 1) == state:
            start -= 1
        status = {"state": state, "since": t(start), "close": _plain(bars[last]["c"]), "lower": out[-1]["lower_now"], "upper": out[-1]["upper_now"]}
    return {**empty, "bases": listed, "zero": zero, "points": points, "channels": out, "status": status, "breaks": breaks,
            "reason": None if out else "Cần ít nhất 2 đáy vùng từ điểm 0 để có kênh"}
