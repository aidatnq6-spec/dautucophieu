"""Đáy nhịp tuần và kênh tăng: weekly MACD base zones and the rising channels drawn through them, on a linear price scale.

Rules (no hand-picked points, nothing known before it happened):
- Weekly bars from daily ones (week keyed by its Monday): highest high, lowest low, last close. Rows with closes only (the
  Vĩ mô series) use the close for all three. The week still running is shown but never used.
- MACD 12/26/9 on weekly closes, as on the Xu hướng board. A base zone runs from a bearish cross (MACD under its signal) to the
  next bullish cross; its low is the lowest weekly low in between. The zone drawn starts two weeks before the low (not before the
  bearish cross) and ends at the bullish cross. A base is known only from its bullish cross.
- Point 0 = the lowest base low within the owner's last N years. Point 2 = the next base, point 1 = the highest high between.
- Channels = edges of the lower convex hull through the bases from point 0: each base joins at the flattest point of its zone as
  seen from the previous joining point (not always the zone's lowest); a point on or above the line to the next one is
  dropped, so lows on one straight line make one channel. Rising lows that keep getting steeper give basic → tăng tốc → final, as on a linear chart. Upper line: parallel through
  the highest high between the two joining points; the dotted line is twice that width.
- Values are given at the last finished week only; the lines are not drawn into the future.
- A break = the first finished week whose close is under the final channel in force that week (built only from bases confirmed by
  then). Not a recommendation.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .indicators import MIN_MACD_BARS, macd

_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")


def _q(value: Decimal, q: Decimal = _Q2) -> str:
    return str(value.quantize(q, ROUND_HALF_UP))


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def weekly_bars(daily: list[dict]) -> list[dict]:
    weeks: dict[date, dict] = {}
    for b in daily:
        c = Decimal(str(b["c"]))
        h, low = Decimal(str(b.get("h", c))), Decimal(str(b.get("l", c)))
        key = _monday(date.fromisoformat(str(b["t"])[:10]))
        w = weeks.get(key)
        weeks[key] = {"t": key, "h": h, "l": low, "c": c} if w is None else {"t": key, "h": max(w["h"], h), "l": min(w["l"], low), "c": c}
    return [weeks[k] for k in sorted(weeks)]


def find_bases(weeks: list[dict], line: list, signal: list) -> list[dict]:
    diff = [None if a is None or s is None else a - s for a, s in zip(line, signal)]
    out, start = [], None
    for i in range(1, len(weeks)):
        if diff[i] is None or diff[i - 1] is None:
            continue
        if diff[i] <= 0 < diff[i - 1]:
            start = i
        elif diff[i] > 0 >= diff[i - 1] and start is not None:
            low_i = min(range(start, i + 1), key=lambda k: (weeks[k]["l"], k))
            first = max(start, low_i - 2)
            out.append({"cross": weeks[i]["t"], "low_date": weeks[low_i]["t"], "low": weeks[low_i]["l"], "zone_from": weeks[first]["t"],
                        "zone_to": weeks[i]["t"], "zone": [(weeks[k]["t"], weeks[k]["l"]) for k in range(first, i + 1)]})
            start = None
    return out


def _years_before(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def point_zero(bases: list[dict], *, last: date, years: int) -> int | None:
    cutoff = _years_before(last, years)
    inside = [i for i, b in enumerate(bases) if b["low_date"] >= cutoff]
    return min(inside, key=lambda i: (bases[i]["low"], bases[i]["low_date"])) if inside else None


def _slope(a: tuple, b: tuple) -> Decimal:
    return (b[1] - a[1]) / Decimal((b[0] - a[0]).days)


def line_at(a: tuple, b: tuple, day: date) -> Decimal:
    return a[1] + _slope(a, b) * (day - a[0]).days


def hull(chain: list[dict]) -> list[tuple[date, Decimal]]:
    """Joining points of the lower convex hull: point 0's low, then each later base at its flattest point seen from the last one."""
    pts = [(chain[0]["low_date"], chain[0]["low"])]
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


def _channel(kind: str, a: tuple, b: tuple, weeks: list[dict], now: date) -> dict:
    top = max((w for w in weeks if a[0] <= w["t"] <= b[0]), key=lambda w: (w["h"], w["t"]))
    width = top["h"] - line_at(a, b, top["t"])
    lower = line_at(a, b, now)
    return {"kind": kind, "from": {"date": a[0].isoformat(), "price": _plain(a[1])}, "to": {"date": b[0].isoformat(), "price": _plain(b[1])},
            "slope": _q(_slope(a, b) * 7, _Q4), "top": {"date": top["t"].isoformat(), "price": _plain(top["h"])},
            "lower_now": _q(lower), "upper_now": _q(lower + width), "double_now": _q(lower + 2 * width)}


def _state(close: Decimal, lower: Decimal, upper: Decimal) -> str:
    return "below" if close < lower else "above" if close > upper else "inside"


def weekly_channels(daily: list[dict], *, today: date, years: int) -> dict:
    weeks = weekly_bars(daily)
    empty = {"bases": [], "zero": None, "points": {}, "channels": [], "status": None, "breaks": [], "in_progress": None,
             "last_week": None, "years": years, "weeks": len(weeks)}
    if not weeks:
        return {**empty, "reason": "Chưa có dữ liệu giá"}
    in_progress = None
    if weeks[-1]["t"] == _monday(today):
        running = weeks.pop()
        in_progress = {"t": running["t"].isoformat(), "c": _plain(running["c"])}
    empty.update(in_progress=in_progress, weeks=len(weeks))
    if len(weeks) < MIN_MACD_BARS:
        return {**empty, "reason": f"Chỉ có {len(weeks)} tuần, cần ít nhất {MIN_MACD_BARS} tuần để có MACD tuần"}
    last = weeks[-1]["t"]
    empty["last_week"] = last.isoformat()
    line, signal = macd([float(w["c"]) for w in weeks])
    every = find_bases(weeks, line, signal)
    cutoff = _years_before(last, years)
    bases = [b for b in every if b["low_date"] >= cutoff]
    zero = point_zero(bases, last=last, years=years)
    listed = [{"cross": b["cross"].isoformat(), "low_date": b["low_date"].isoformat(), "low": _plain(b["low"]), "zone_from": b["zone_from"].isoformat(),
               "zone_to": b["zone_to"].isoformat(), "vs_prev": None if i == 0 else "higher" if b["low"] > bases[i - 1]["low"] else "lower"}
              for i, b in enumerate(bases)]
    if zero is None:
        return {**empty, "bases": listed, "reason": f"Không có đáy vùng MACD nào trong {years} năm"}
    chain = bases[zero:]
    points = {"0": {"date": chain[0]["low_date"].isoformat(), "price": _plain(chain[0]["low"])}}
    if len(chain) > 1:
        two = chain[1]
        between = [w for w in weeks if chain[0]["low_date"] < w["t"] < two["low_date"]]
        if between:
            one = max(between, key=lambda w: (w["h"], w["t"]))
            points["1"] = {"date": one["t"].isoformat(), "price": _plain(one["h"])}
        points["2"] = {"date": two["low_date"].isoformat(), "price": _plain(two["low"])}
    pts = hull(chain)
    edges = list(zip(pts, pts[1:]))
    kinds = ["final"] if len(edges) == 1 else ["basic"] + [f"accel{k}" for k in range(1, len(edges) - 1)] + ["final"]
    channels = [_channel(k, a, b, weeks, last) for k, (a, b) in zip(kinds, edges)]

    # Breaks: each finished week against the final channel in force then (bases confirmed by that week only).
    breaks, was_below, cache = [], False, {}
    for w in weeks:
        n = sum(1 for b in chain if b["cross"] <= w["t"])  # bases are in time order, so the count names the known ones
        if n < 2:
            continue
        if n not in cache:
            cache[n] = hull(chain[:n])
        hp = cache[n]
        if len(hp) < 2 or w["t"] <= hp[-1][0]:
            was_below = False
            continue
        lower = line_at(hp[-2], hp[-1], w["t"])
        below = w["c"] < lower
        if below and not was_below:
            breaks.append({"date": w["t"].isoformat(), "close": _plain(w["c"]), "lower": _q(lower),
                           "from": {"date": hp[-2][0].isoformat(), "price": _plain(hp[-2][1])}, "to": {"date": hp[-1][0].isoformat(), "price": _plain(hp[-1][1])}})
        was_below = below

    status = None
    if channels:
        a, b = edges[-1]
        width = Decimal(channels[-1]["upper_now"]) - Decimal(channels[-1]["lower_now"])
        def at(w):
            lo = line_at(a, b, w["t"])
            return _state(w["c"], lo, lo + width)
        state, since = at(weeks[-1]), weeks[-1]["t"]
        for w in reversed(weeks[:-1]):
            if w["t"] <= b[0] or at(w) != state:
                break
            since = w["t"]
        status = {"state": state, "since": since.isoformat(), "close": _plain(weeks[-1]["c"]), "lower": channels[-1]["lower_now"],
                  "upper": channels[-1]["upper_now"]}
    return {**empty, "bases": listed, "zero": zero, "points": points, "channels": channels, "status": status, "breaks": breaks,
            "reason": None if channels else "Cần ít nhất 2 đáy vùng từ điểm 0 để có kênh"}
