"""Đèn tín hiệu rủi ro vĩ mô on Vĩ mô (spec 2026-11-21): five lights (green, yellow, red) on data already stored, with the
owner-approved thresholds (27/10/2026). A figure past its light's age is "stale", never coloured. A Telegram line is sent only when a
light changes level. Describes the data; never recommends."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

WINDOW = timedelta(days=30)
# id: (name, yellow, red)
SIGNALS = {
    "oil": ("Giá dầu WTI", Decimal("0.10"), Decimal("0.20")),                       # change over 30 days
    "usd": ("Đồng USD (chỉ số rộng của Fed)", Decimal("0.02"), Decimal("0.04")),     # change over 30 days
    "fx_gap": ("Tỷ giá tự do so với Vietcombank", Decimal("0.01"), Decimal("0.02")),  # free selling rate above VCB's
    "foreign": ("Khối ngoại", Decimal(5), Decimal(10)),                               # consecutive net-selling sessions
    "interbank": ("Lãi suất liên ngân hàng qua đêm", Decimal(5), Decimal(7)),         # %/năm
}
# days after which a light's latest figure no longer stands for today (oil daily, the broad dollar weekly-ish on FRED, the rest daily)
MAX_AGE_DAYS = {"oil": 10, "usd": 14, "fx_gap": 7, "foreign": 7, "interbank": 7}
LEVEL_WORD = {"green": "xanh", "yellow": "vàng", "red": "đỏ"}

Points = list[tuple[date, Decimal]]


def _plain(value: Decimal) -> str:
    return "0" if value == 0 else format(value.normalize(), "f")


def _ratio(value: Decimal) -> str:
    return _plain(value.quantize(Decimal("0.0001"), ROUND_HALF_UP))


def _level(value: Decimal, yellow: Decimal, red: Decimal) -> str:
    return "red" if value >= red else "yellow" if value >= yellow else "green"


def _light(key: str, value: Decimal | None, shown: str | None, latest: date | None, spark: Points, first: date | None,
           today: date) -> dict:
    name, yellow, red = SIGNALS[key]
    since = first.isoformat() if first is not None and latest is not None and first > latest - WINDOW else None
    level = "missing" if value is None else "stale" if (today - latest).days > MAX_AGE_DAYS[key] else _level(value, yellow, red)
    return {"id": key, "name": name, "level": level, "value": shown, "max_age_days": MAX_AGE_DAYS[key],
            "latest_date": latest.isoformat() if latest else None, "yellow": str(yellow), "red": str(red), "since": since,
            "spark": [{"date": d.isoformat(), "value": v} for d, v in spark]}


def _recent(points: Points, latest: date) -> Points:
    return [(d, v) for d, v in points if d >= latest - WINDOW]


def _change(key: str, points: Points, today: date) -> dict:
    if not points:
        return _light(key, None, None, None, [], None, today)
    latest = points[-1]
    earlier = [p for p in points if p[0] <= latest[0] - WINDOW]
    spark = [(d, _plain(v)) for d, v in _recent(points, latest[0])]
    if not earlier or earlier[-1][1] == 0:
        return _light(key, None, None, latest[0], spark, points[0][0], today)
    change = latest[1] / earlier[-1][1] - 1
    return _light(key, change, _ratio(change), latest[0], spark, points[0][0], today)


def _fx_gap(free: Points, vcb: Points, today: date) -> dict:
    rates = dict(vcb)
    gaps = [(d, v / rates[d] - 1) for d, v in free if rates.get(d)]
    if not gaps:
        return _light("fx_gap", None, None, None, [], None, today)
    latest = gaps[-1]
    return _light("fx_gap", latest[1], _ratio(latest[1]), latest[0], [(d, _ratio(g)) for d, g in _recent(gaps, latest[0])], gaps[0][0], today)


def _foreign(points: Points, today: date) -> dict:
    if not points:
        return _light("foreign", None, None, None, [], None, today)
    streak = 0
    for _, v in reversed(points):
        if v >= 0:
            break
        streak += 1
    latest = points[-1][0]
    return _light("foreign", Decimal(streak), str(streak), latest, [(d, _plain(v)) for d, v in _recent(points, latest)], points[0][0], today)


def _interbank(points: Points, today: date) -> dict:
    if not points:
        return _light("interbank", None, None, None, [], None, today)
    latest = points[-1]
    return _light("interbank", latest[1], _plain(latest[1]), latest[0], [(d, _plain(v)) for d, v in _recent(points, latest[0])], points[0][0], today)


def macro_signals(series: dict[str, Points], *, today: date) -> list[dict]:
    """series: factor_oil, factor_usd, usd_vnd_free, usd_vnd_vcb, foreign_net, vn_interbank_on (oldest first); each light reads its
    own latest observation, judged against today for its age."""
    return [_change("oil", series.get("factor_oil") or [], today), _change("usd", series.get("factor_usd") or [], today),
            _fx_gap(series.get("usd_vnd_free") or [], series.get("usd_vnd_vcb") or [], today), _foreign(series.get("foreign_net") or [], today),
            _interbank(series.get("vn_interbank_on") or [], today)]


def _pct(value: str, digits: int, sign: bool = True) -> str:
    return f"{Decimal(value) * 100:{'+' if sign else ''}.{digits}f}".replace(".", ",")


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
