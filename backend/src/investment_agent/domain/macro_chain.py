"""Chuỗi tác động vĩ mô on Vĩ mô: oil → Vietnam inflation → Vietnam rates → foreign flows → VN-Index, the chain the owner saw on a
war-watch page. Each link reads its direction over about a month from data already stored and whether that weighs on stocks.
Descriptive only: no recommendation, no model."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

MONTH = timedelta(days=30)
OIL_BAND, INDEX_BAND = Decimal("0.05"), Decimal("0.03")      # share moves
CPI_BAND, RATE_BAND = Decimal("0.2"), Decimal("0.25")         # percentage points
FOREIGN_SESSIONS = 20
STALE_DAYS = {"oil": 10, "inflation": 45, "rates": 10, "foreign": 7, "vnindex": 7}
RATES = ("vn_interbank_on", "vn10y")

Points = list[tuple[date, Decimal]]


def _plain(value: Decimal) -> str:
    return "0" if value == 0 else format(value.normalize(), "f")


def _ratio(value: Decimal) -> str:
    return _plain(value.quantize(Decimal("0.0001"), ROUND_HALF_UP))


def _pp(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), ROUND_HALF_UP))


def _latest(points: Points) -> dict:
    return {"date": points[-1][0].isoformat(), "value": _plain(points[-1][1])}


def _base(points: Points) -> tuple[tuple[date, Decimal], bool]:
    """The last point at least a month before the latest one; the earliest point (short history) when there is none."""
    earlier = [p for p in points if p[0] <= points[-1][0] - MONTH]
    return (earlier[-1], False) if earlier else (points[0], True)


def _direction(change: Decimal, band: Decimal) -> str:
    return "up" if change > band else "down" if change < -band else "flat"


def _stale(points: Points, node: str, today: date) -> bool:
    return (today - points[-1][0]).days > STALE_DAYS[node]


def _effect(direction: str | None, *, pressure_when: str) -> str:
    if direction in (None, "flat"):
        return "neutral"
    return "pressure" if direction == pressure_when else "support"


def _missing(node: str) -> dict:
    return {"id": node, "direction": None, "effect": "missing", "latest": None, "stale": False}


def _share_move(node: str, points: Points, band: Decimal, *, pressure_when: str, today: date) -> dict:
    if not points:
        return _missing(node)
    (start, then), short = _base(points)
    change = points[-1][1] / then - 1 if then else Decimal(0)
    direction = _direction(change, band) if len(points) > 1 else None
    return {"id": node, "direction": direction, "effect": _effect(direction, pressure_when=pressure_when), "latest": _latest(points),
            "from": start.isoformat(), "change": _ratio(change), "short_history": short, "stale": _stale(points, node, today)}


def _inflation(points: Points, today: date) -> dict:
    if not points:
        return _missing("inflation")
    if len(points) < 2:
        return {"id": "inflation", "direction": None, "effect": "neutral", "latest": _latest(points), "from": None, "change": None,
                "short_history": True, "stale": _stale(points, "inflation", today)}
    change = points[-1][1] - points[-2][1]  # month on month of the year-on-year figure
    direction = _direction(change, CPI_BAND)
    return {"id": "inflation", "direction": direction, "effect": _effect(direction, pressure_when="up"), "latest": _latest(points),
            "from": points[-2][0].isoformat(), "change": _pp(change), "short_history": False, "stale": _stale(points, "inflation", today)}


def _rates(series: dict[str, Points], today: date) -> dict:
    parts = []
    for key in RATES:
        points = series.get(key) or []
        if not points:
            continue
        (start, then), short = _base(points)
        change = points[-1][1] - then
        parts.append({"id": key, "direction": _direction(change, RATE_BAND) if len(points) > 1 else None, "latest": _latest(points),
                      "from": start.isoformat(), "change": _pp(change), "short_history": short, "stale": _stale(points, "rates", today)})
    if not parts:
        return _missing("rates")
    moves = {p["direction"] for p in parts} - {"flat", None}
    direction = moves.pop() if len(moves) == 1 else "flat"  # rates moving apart read as flat
    return {"id": "rates", "direction": direction, "effect": _effect(direction, pressure_when="up"), "latest": None, "parts": parts,
            "short_history": any(p["short_history"] for p in parts), "stale": any(p["stale"] for p in parts)}


def _foreign(points: Points, today: date) -> dict:
    if not points:
        return _missing("foreign")
    window = points[-FOREIGN_SESSIONS:]
    net = sum((v for _, v in window), Decimal(0))
    direction = "buy" if net > 0 else "sell" if net < 0 else "flat"
    return {"id": "foreign", "direction": direction, "effect": _effect(direction, pressure_when="sell"),
            "latest": {"date": window[-1][0].isoformat(), "value": _plain(net)}, "from": window[0][0].isoformat(), "sessions": len(window),
            "short_history": len(window) < FOREIGN_SESSIONS, "stale": _stale(points, "foreign", today)}


def macro_chain(series: dict[str, Points], *, today: date) -> dict:
    """series: wti, vn_cpi_yoy, vn_interbank_on, vn10y, foreign_net (tỷ đồng per session) and vnindex (points), oldest first."""
    nodes = [
        _share_move("oil", series.get("wti") or [], OIL_BAND, pressure_when="up", today=today),
        _inflation(series.get("vn_cpi_yoy") or [], today),
        _rates(series, today),
        _foreign(series.get("foreign_net") or [], today),
        _share_move("vnindex", series.get("vnindex") or [], INDEX_BAND, pressure_when="down", today=today),
    ]
    return {"nodes": nodes, **{k: [n["id"] for n in nodes if n["effect"] == k] for k in ("pressure", "support", "missing")}}
