"""Chuỗi giá trị: whether the stored macro series currently help or hurt each value chain.

Each factor ties one stored series to a stage of the chain and says whether a rise is good or bad for it. A series reads up,
down or flat over about a month (PMI against 50; foreign flows by the sign of 20 sessions), and the chain's card weighs the
factors chính 3, phụ 2, nhỏ 1. Descriptive only: no recommendation, no model.
"""

from datetime import date
from decimal import Decimal

from .macro_chain import FOREIGN_SESSIONS, _base, _plain, _pp, _ratio

WEIGHTS = {"major": 3, "minor": 2, "small": 1}
MAJOR_SHARE, MINOR_SHARE = Decimal("0.25"), Decimal("0.10")
LEAN = Decimal("0.20")                 # good − bad (or bad − good) needed for Thuận gió / Ngược gió
UNKNOWN_LIMIT = Decimal("0.50")        # beyond this share the card says Chưa đủ dữ liệu
RATES = ("fed_effr", "deposit_12m", "us10y", "vn10y", "vn_interbank_on")
# Relative bands for prices and levels, point bands for rates, inflation and PMI.
SHARE_BANDS = {"wti": Decimal("0.05"), "dxy": Decimal("0.02"), "usd_vnd_free": Decimal("0.01"), "usd_vnd_sbv": Decimal("0.01"),
               "usd_vnd_vcb": Decimal("0.01"), "m2_vn": Decimal("0.01"), "vnindex_value": Decimal("0.15")}
COMMODITY_BAND = Decimal("0.05")
POINT_BANDS = {**{r: Decimal("0.25") for r in RATES}, "vn_cpi_yoy": Decimal("0.2"), "us_cpi_yoy": Decimal("0.2")}
PMI = ("vn_pmi", "us_pmi")

Points = list[tuple[date, Decimal]]


def weight_for_share(share: str) -> str:
    """A reported share, or range "a-b" read at its midpoint: ≥ 25% chính, ≥ 10% phụ, otherwise nhỏ."""
    low, _, high = share.partition("-")
    mid = (Decimal(low) + Decimal(high or low)) / 2
    return "major" if mid >= MAJOR_SHARE else "minor" if mid >= MINOR_SHARE else "small"


def _direction(change: Decimal, band: Decimal) -> str:
    return "up" if change > band else "down" if change < -band else "flat"


def read_indicator(indicator: str, points: Points, *, today: date, max_age_days: int) -> dict | None:
    if not points:
        return None
    last_day, last = points[-1]
    out = {"date": last_day.isoformat(), "value": _plain(last), "stale": (today - last_day).days > max_age_days}
    if indicator == "foreign_net":
        window = points[-FOREIGN_SESSIONS:]
        net = sum((v for _, v in window), Decimal(0))
        return {**out, "direction": "up" if net > 0 else "down" if net < 0 else "flat", "change": _plain(net), "kind": "net",
                "from": window[0][0].isoformat()}
    if len(points) < 2:
        return {**out, "direction": None, "change": None, "kind": None, "from": None}
    if indicator in PMI:
        before = points[-2][1]
        direction = "up" if last >= 50 and last >= before else "down" if last < 50 and last <= before else "flat"
        return {**out, "direction": direction, "change": _pp(last - before), "kind": "points", "from": points[-2][0].isoformat()}
    (start, then), _ = _base(points)
    if indicator in POINT_BANDS:
        change = last - then
        return {**out, "direction": _direction(change, POINT_BANDS[indicator]), "change": _pp(change), "kind": "points",
                "from": start.isoformat()}
    band = SHARE_BANDS.get(indicator, COMMODITY_BAND)
    change = last / then - 1 if then else Decimal(0)
    return {**out, "direction": _direction(change, band), "change": _ratio(change), "kind": "ratio", "from": start.isoformat()}


def factor_status(when_up: str, reading: dict | None) -> str:
    if reading is None or reading["stale"] or reading["direction"] is None:
        return "unknown"
    if reading["direction"] == "flat":
        return "neutral"
    return when_up if reading["direction"] == "up" else ("bad" if when_up == "good" else "good")


def score(factors: list[tuple[str, str]]) -> dict[str, str]:
    """(weight, status) pairs → each status's share of the total weight, as 4-decimal strings."""
    total = sum(WEIGHTS[w] for w, _ in factors)
    q = Decimal("0.0001")
    return {k: str((Decimal(sum(WEIGHTS[w] for w, s in factors if s == k)) / total).quantize(q) if total else Decimal(0).quantize(q))
            for k in ("good", "bad", "neutral", "unknown")}


def label(shares: dict[str, str], *, approved: bool) -> str | None:
    if not approved:
        return None
    good, bad, unknown = (Decimal(shares[k]) for k in ("good", "bad", "unknown"))
    if unknown > UNKNOWN_LIMIT:
        return "insufficient"
    return "tailwind" if good - bad >= LEAN else "headwind" if bad - good >= LEAN else "neutral"
