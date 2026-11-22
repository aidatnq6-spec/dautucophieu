"""Đèn tín hiệu rủi ro vĩ mô on Vĩ mô (spec 2026-11-21): nine lights (normal, warning, danger) on data already stored, with the
owner-approved thresholds (27/10/2026; four more lights and the improvements 21/11/2026). Each light works out what it measures on every
stored day of the last 30, which gives its line, the day its level began, how far the next level is and which way it moved. A figure
past its light's age is "stale", never coloured. A Telegram line is sent only when a light changes level. Describes the data; never
recommends."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

WINDOW = timedelta(days=30)
YEARS_5 = timedelta(days=round(365.25 * 5))
CENTRAL_MAX_GAP = timedelta(days=7)
BAND = Decimal("0.05")  # the bank's band around the central rate


@dataclass(frozen=True)
class Spec:
    name: str
    yellow: Decimal
    red: Decimal
    bad: str            # "up": higher is worse; "down": lower is worse
    strict: bool        # on the falling side: below the mark (PMI) rather than at or below it
    max_age: int        # days after which the latest figure no longer stands for today
    flat: Decimal       # a move smaller than this reads "flat", in the light's own unit
    kind: str           # "share" (a ratio shown in %), "points", "count"
    link: str           # where the light's name leads
    max_sessions: int | None = None  # a HOSE-session light: old after this many sessions without a figure, not max_age days (22/11/2026)


SIGNALS = {
    "oil": Spec("Giá dầu WTI", Decimal("0.10"), Decimal("0.20"), "up", False, 10, Decimal("0.01"), "share", "#chi-so-wti"),
    "usd": Spec("Đồng USD (chỉ số rộng của Fed)", Decimal("0.02"), Decimal("0.04"), "up", False, 14, Decimal("0.002"), "share", "#chi-so-dxy"),
    "fx_gap": Spec("Tỷ giá tự do so với Vietcombank", Decimal("0.01"), Decimal("0.02"), "up", False, 7, Decimal("0.0005"), "share",
                   "#chi-so-usd_vnd_free"),
    "fx_ceiling": Spec("Tỷ giá Vietcombank so với trần", Decimal("0.02"), Decimal("0.01"), "down", False, 7, Decimal("0.001"), "share",
                       "#chi-so-usd_vnd_vcb"),
    "us10y": Spec("Lợi suất trái phiếu Mỹ 10 năm", Decimal("0.3"), Decimal("0.5"), "up", False, 10, Decimal("0.05"), "points", "#chi-so-us10y"),
    "foreign": Spec("Khối ngoại", Decimal(5), Decimal(10), "up", False, 7, Decimal("0.5"), "count", "#chi-so-foreign_net", 5),
    "interbank": Spec("Lãi suất liên ngân hàng qua đêm", Decimal(5), Decimal(7), "up", False, 7, Decimal("0.1"), "points",
                      "#chi-so-vn_interbank_on", 5),
    "pe": Spec("P/E VN-Index so với 5 năm", Decimal("0.80"), Decimal("0.90"), "up", False, 7, Decimal("0.02"), "share", "/fair-value", 5),
    "pmi": Spec("PMI sản xuất Việt Nam", Decimal(50), Decimal(48), "down", True, 45, Decimal("0.3"), "points", "#chi-so-vn_pmi"),
}
LEVEL_WORD = {"green": "bình thường", "yellow": "cảnh báo", "red": "nguy hiểm"}

Points = list[tuple[date, Decimal]]


def _plain(value: Decimal) -> str:
    return "0" if value == 0 else format(value.normalize(), "f")


def _ratio(value: Decimal) -> str:
    return _plain(value.quantize(Decimal("0.0001"), ROUND_HALF_UP))


def _show(key: str, value: Decimal) -> str:
    return _ratio(value) if SIGNALS[key].kind == "share" else _plain(value.quantize(Decimal("0.01"), ROUND_HALF_UP))


def _level(key: str, value: Decimal) -> str:
    s = SIGNALS[key]
    if s.bad == "up":
        return "red" if value >= s.red else "yellow" if value >= s.yellow else "green"
    below = (lambda mark: value < mark) if s.strict else (lambda mark: value <= mark)
    return "red" if below(s.red) else "yellow" if below(s.yellow) else "green"


def _next(key: str, value: Decimal) -> dict | None:
    """The next level towards the bad side and how far it is in the light's own unit; None once at danger."""
    s, level = SIGNALS[key], _level(key, value)
    if level == "red":
        return None
    target = s.yellow if level == "green" else s.red
    return {"level": "yellow" if level == "green" else "red", "by": _show(key, abs(target - value))}


def _against_30(points: Points, share: bool) -> Points:
    """Each day's change against the latest figure at least 30 days before: a share, or a difference in points."""
    out, j = [], -1
    for d, v in points:
        while j + 1 < len(points) and points[j + 1][0] <= d - WINDOW:
            j += 1
        if j >= 0 and (not share or points[j][1] != 0):
            out.append((d, v / points[j][1] - 1 if share else v - points[j][1]))
    return out


def _ceiling_room(vcb: Points, central: Points) -> Points:
    """The room left under the band's ceiling each Vietcombank day, from the central rate of that day or up to 7 days before."""
    out, central = [], sorted(central)
    for d, v in vcb:
        set_on = [(c, r) for c, r in central if c <= d]
        if set_on and d - set_on[-1][0] <= CENTRAL_MAX_GAP and v:
            out.append((d, set_on[-1][1] * (1 + BAND) / v - 1))
    return out


def _percentile(points: Points, since: date) -> Points:
    """From `since` on: each day's share of the sessions of the five years up to it whose P/E was at or below that day's."""
    out = []
    for i, (d, v) in enumerate(points):
        if d < since:
            continue
        window = [x for e, x in points[:i + 1] if e > d - YEARS_5]
        out.append((d, Decimal(sum(1 for x in window if x <= v)) / len(window)))
    return out


# the stored series each light reads; the first is the one its history starts from
SOURCES = {"oil": "factor_oil", "usd": "factor_usd", "fx_gap": "usd_vnd_free", "fx_ceiling": "usd_vnd_vcb", "us10y": "us10y",
           "foreign": "foreign_net", "interbank": "vn_interbank_on", "pe": "vnindex_pe", "pmi": "vn_pmi"}


def _measured(key: str, series: dict[str, Points]) -> Points:
    """What the light measures on each stored day, oldest first."""
    get = lambda k: series.get(k) or []  # noqa: E731
    if key in ("oil", "usd"):
        return _against_30(get(SOURCES[key]), share=True)
    if key == "us10y":
        return _against_30(get("us10y"), share=False)
    if key == "fx_gap":
        rates = dict(get("usd_vnd_vcb"))
        return [(d, v / rates[d] - 1) for d, v in get("usd_vnd_free") if rates.get(d)]
    if key == "fx_ceiling":
        return _ceiling_room(get("usd_vnd_vcb"), get("usd_vnd_central"))
    if key == "foreign":
        out, run = [], 0
        for d, v in get("foreign_net"):
            run = run + 1 if v < 0 else 0
            out.append((d, Decimal(run)))
        return out
    if key == "pe":
        pe = get("vnindex_pe")
        return _percentile(pe, pe[-1][0] - WINDOW) if pe else []
    return list(get(SOURCES[key]))


def _move(key: str, measured: Points) -> dict | None:
    """Which way the light's measure went and whether that way is the bad one."""
    if not measured:
        return None
    s = SIGNALS[key]
    latest, value = measured[-1]
    if key == "foreign":
        direction = "up" if value > 0 else "down"
        return {"direction": direction, "bad": direction == "up", "by": _plain(value)}
    if key in ("oil", "usd", "us10y"):  # the measure is itself a 30-day change
        change = value
    else:
        base = [v for d, v in measured if d <= latest - WINDOW] or [measured[0][1]]
        change = value - base[-1]
    direction = "flat" if abs(change) < s.flat else "up" if change > 0 else "down"
    return {"direction": direction, "bad": None if direction == "flat" else direction == s.bad, "by": _show(key, abs(change))}


def _sessions_after(latest: date, today: date, is_session) -> int:
    return sum(1 for i in range(1, (today - latest).days + 1) if is_session(latest + timedelta(days=i)))


def _light(key: str, measured: Points, raw: Points, today: date, is_session) -> dict:
    s = SIGNALS[key]
    out = {"id": key, "name": s.name, "level": "missing", "value": None, "max_age_days": s.max_age, "max_age_sessions": s.max_sessions, "yellow": str(s.yellow),
           "red": str(s.red), "bad_side": s.bad, "strict": s.strict, "down_yellow": None, "down_red": None,
           "latest_date": raw[-1][0].isoformat() if raw else None, "since": None, "spark": [], "next": None,
           "level_since": None, "level_since_open": False, "link": s.link, "move": None, "pe": None}
    if not measured:
        return out
    latest, value = measured[-1]
    recent = [(d, v) for d, v in measured if d >= latest - WINDOW]
    held = _level(key, value)
    old = _sessions_after(latest, today, is_session) > s.max_sessions if s.max_sessions else (today - latest).days > s.max_age
    level = "stale" if old else held
    start = len(recent) - 1
    while start > 0 and _level(key, recent[start - 1][1]) == held:
        start -= 1
    first = raw[0][0] if raw else None
    history = YEARS_5 if key == "pe" else WINDOW
    return {**out, "level": level, "value": _show(key, value), "latest_date": latest.isoformat(),
            "since": first.isoformat() if first is not None and first > latest - history else None,
            "spark": [{"date": d.isoformat(), "value": _show(key, v)} for d, v in recent],
            "next": None if level == "stale" else _next(key, value), "move": _move(key, measured),
            # the whole window at one level, with older days stored: it began on that day or earlier
            "level_since": recent[start][0].isoformat(), "level_since_open": start == 0 and measured[0][0] < recent[0][0],
            "pe": _plain(raw[-1][1].quantize(Decimal("0.01"), ROUND_HALF_UP)) if key == "pe" else None}


def macro_signals(series: dict[str, Points], *, today: date, is_session=None) -> list[dict]:
    """series: factor_oil, factor_usd, usd_vnd_free, usd_vnd_vcb, usd_vnd_central, us10y, foreign_net, vn_interbank_on, vnindex_pe,
    vn_pmi (oldest first); each light reads its own latest observation, judged against today for its age."""
    if is_session is None:
        from investment_agent.market.sessions import is_session
    return [_light(k, _measured(k, series), series.get(SOURCES[k]) or [], today, is_session) for k in SIGNALS]


def _pct(value: str, digits: int, sign: bool = True) -> str:
    return f"{Decimal(value) * 100:{'+' if sign else ''}.{digits}f}".replace(".", ",").replace("-", "−")


def _detail(s: dict) -> str:
    v = s["value"]
    if s["id"] in ("oil", "usd"):
        return f"{_pct(v, 1)}% trong 30 ngày"
    if s["id"] == "fx_gap":
        return f"tự do cao hơn {_pct(v, 2, sign=False)}%"
    if s["id"] == "fx_ceiling":
        return f"còn {_pct(v, 2, sign=False)}% tới trần"
    if s["id"] == "us10y":
        return f"{'+' if Decimal(v) > 0 else ''}{v.replace('.', ',').replace('-', '−')} điểm % trong 30 ngày"
    if s["id"] == "foreign":
        return f"bán ròng {v} phiên liên tiếp"
    if s["id"] == "pe":
        return f"P/E {s['pe'].replace('.', ',')}, cao hơn hoặc bằng {_pct(v, 0, sign=False)}% số phiên 5 năm"
    if s["id"] == "pmi":
        return f"PMI {v.replace('.', ',')}"
    return f"{v.replace('.', ',')}%/năm"


def signal_changes(previous: dict[str, str] | None, current: list[dict]) -> list[str]:
    """One line per light that moved between its levels since the last run; nothing on the first run or to/from missing or stale. A
    light added later has no earlier level, so its first reading says nothing either."""
    if previous is None:
        return []
    lines = []
    for s in current:
        before = previous.get(s["id"])
        if before in LEVEL_WORD and s["level"] in LEVEL_WORD and before != s["level"]:
            lines.append(f"{s['name']}: {LEVEL_WORD[before]} → {LEVEL_WORD[s['level']]} ({_detail(s)})")
    return lines
