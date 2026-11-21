"""Đèn tín hiệu rủi ro vĩ mô on Vĩ mô (spec 2026-11-21): five lights (green, yellow, red) on data already stored, with the
owner-approved thresholds (27/10/2026; oil's falling side and the other improvements 21/11/2026). Each light works out what it measures
on every stored day of the last 30, which gives its line, the day its level began and how far the next level is. A figure past its
light's age is "stale", never coloured. A Telegram line is sent only when a light changes level. Describes the data; never recommends."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

WINDOW = timedelta(days=30)
# id: (name, yellow, red), on the rising side
SIGNALS = {
    "oil": ("Giá dầu WTI", Decimal("0.10"), Decimal("0.20")),                       # change over 30 days
    "usd": ("Đồng USD (chỉ số rộng của Fed)", Decimal("0.02"), Decimal("0.04")),     # change over 30 days
    "fx_gap": ("Tỷ giá tự do so với Vietcombank", Decimal("0.01"), Decimal("0.02")),  # free selling rate above VCB's
    "foreign": ("Khối ngoại", Decimal(5), Decimal(10)),                               # consecutive net-selling sessions
    "interbank": ("Lãi suất liên ngân hàng qua đêm", Decimal(5), Decimal(7)),         # %/năm
}
# the falling side, where a fall is a risk too: oil down hard tells of a weakening world economy (owner, 21/11/2026)
DOWN = {"oil": (Decimal("-0.15"), Decimal("-0.25"))}
# days after which a light's latest figure no longer stands for today (oil daily, the broad dollar weekly-ish on FRED, the rest daily)
MAX_AGE_DAYS = {"oil": 10, "usd": 14, "fx_gap": 7, "foreign": 7, "interbank": 7}
# the row of Vĩ mô's table nearest to what each light measures
LINK = {"oil": "wti", "usd": "dxy", "fx_gap": "usd_vnd_free", "foreign": "foreign_net", "interbank": "vn_interbank_on"}
LEVEL_WORD = {"green": "xanh", "yellow": "vàng", "red": "đỏ"}
RANK = {"green": 0, "yellow": 1, "red": 2}

Points = list[tuple[date, Decimal]]


def _plain(value: Decimal) -> str:
    return "0" if value == 0 else format(value.normalize(), "f")


def _ratio(value: Decimal) -> str:
    return _plain(value.quantize(Decimal("0.0001"), ROUND_HALF_UP))


def _show(key: str, value: Decimal) -> str:
    return _ratio(value) if key in ("oil", "usd", "fx_gap") else _plain(value)


def _level(key: str, value: Decimal) -> str:
    _, yellow, red = SIGNALS[key]
    up = "red" if value >= red else "yellow" if value >= yellow else "green"
    if key not in DOWN:
        return up
    down_yellow, down_red = DOWN[key]
    down = "red" if value <= down_red else "yellow" if value <= down_yellow else "green"
    return max(up, down, key=RANK.get)


def _next(key: str, value: Decimal) -> dict | None:
    """The next level on the side the value is on, and how far it is in the light's own unit; None once red."""
    _, yellow, red = SIGNALS[key]
    marks = (yellow, red)
    if key in DOWN and value < 0:
        marks = DOWN[key]
    level = _level(key, value)
    if level == "red":
        return None
    target = marks[0] if level == "green" else marks[1]
    return {"level": "yellow" if level == "green" else "red", "by": _show(key, abs(target - value))}


def _measured(key: str, series: dict[str, Points]) -> Points:
    """What the light measures on each stored day, oldest first."""
    if key in ("oil", "usd"):
        points = series.get("factor_oil" if key == "oil" else "factor_usd") or []
        out, j = [], -1
        for d, v in points:
            while j + 1 < len(points) and points[j + 1][0] <= d - WINDOW:
                j += 1
            if j >= 0 and points[j][1] != 0:
                out.append((d, v / points[j][1] - 1))
        return out
    if key == "fx_gap":
        rates = dict(series.get("usd_vnd_vcb") or [])
        return [(d, v / rates[d] - 1) for d, v in series.get("usd_vnd_free") or [] if rates.get(d)]
    if key == "foreign":
        out, run = [], 0
        for d, v in series.get("foreign_net") or []:
            run = run + 1 if v < 0 else 0
            out.append((d, Decimal(run)))
        return out
    return list(series.get("vn_interbank_on") or [])


def _since(key: str, first_of: Points, latest: date) -> date | None:
    """The first stored day when fewer than 30 days of what the light reads are kept, else None."""
    first = first_of[0][0] if first_of else None
    return first if first is not None and first > latest - WINDOW else None


def _light(key: str, measured: Points, raw: Points, today: date) -> dict:
    name, yellow, red = SIGNALS[key]
    down = DOWN.get(key)
    out = {"id": key, "name": name, "level": "missing", "value": None, "max_age_days": MAX_AGE_DAYS[key], "yellow": str(yellow),
           "red": str(red), "down_yellow": str(down[0]) if down else None, "down_red": str(down[1]) if down else None,
           "latest_date": raw[-1][0].isoformat() if raw else None, "since": None, "spark": [], "next": None,
           "level_since": None, "level_since_open": False, "link": LINK[key]}
    if not measured:
        return out
    latest, value = measured[-1]
    recent = [(d, v) for d, v in measured if d >= latest - WINDOW]
    level = "stale" if (today - latest).days > MAX_AGE_DAYS[key] else _level(key, value)
    held = _level(key, value)
    start = len(recent) - 1
    while start > 0 and _level(key, recent[start - 1][1]) == held:
        start -= 1
    return {**out, "level": level, "value": _show(key, value), "latest_date": latest.isoformat(), "since": (s.isoformat() if (s := _since(key, raw, latest)) else None),
            "spark": [{"date": d.isoformat(), "value": _show(key, v)} for d, v in recent],
            "next": None if level == "stale" else _next(key, value),
            # the whole window at one level, with older days stored: it began on that day or earlier
            "level_since": recent[start][0].isoformat(), "level_since_open": start == 0 and measured[0][0] < recent[0][0]}


def macro_signals(series: dict[str, Points], *, today: date) -> list[dict]:
    """series: factor_oil, factor_usd, usd_vnd_free, usd_vnd_vcb, foreign_net, vn_interbank_on (oldest first); each light reads its
    own latest observation, judged against today for its age."""
    raw = {"oil": series.get("factor_oil") or [], "usd": series.get("factor_usd") or [],
           "fx_gap": [(d, v) for d, v in series.get("usd_vnd_free") or [] if dict(series.get("usd_vnd_vcb") or []).get(d)],
           "foreign": series.get("foreign_net") or [], "interbank": series.get("vn_interbank_on") or []}
    return [_light(k, _measured(k, series), raw[k], today) for k in SIGNALS]


def _pct(value: str, digits: int, sign: bool = True) -> str:
    return f"{Decimal(value) * 100:{'+' if sign else ''}.{digits}f}".replace(".", ",").replace("-", "−")


def _detail(s: dict) -> str:
    if s["id"] in ("oil", "usd"):
        return f"{_pct(s['value'], 1)}% trong 30 ngày"
    if s["id"] == "fx_gap":
        return f"tự do cao hơn {_pct(s['value'], 2, sign=False)}%"
    if s["id"] == "foreign":
        return f"bán ròng {s['value']} phiên liên tiếp"
    return f"{s['value'].replace('.', ',')}%/năm"


def signal_changes(previous: dict[str, str] | None, current: list[dict]) -> list[str]:
    """One line per light that moved between green, yellow and red since the last run; nothing on the first run or to/from missing."""
    if previous is None:
        return []
    lines = []
    for s in current:
        before = previous.get(s["id"])
        if before in LEVEL_WORD and s["level"] in LEVEL_WORD and before != s["level"]:
            lines.append(f"{s['name']}: {LEVEL_WORD[before]} → {LEVEL_WORD[s['level']]} ({_detail(s)})")
    return lines
