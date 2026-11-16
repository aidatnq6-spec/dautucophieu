"""Chuỗi liên thị trường trong tuần on Vĩ mô: US inflation → US rates (EFFR, 10-year yield) → DXY → gold → USD/VND, the chain the
"lạm phát Mỹ nóng trở lại" talk walked through (16/11/2026). Each market link reads its move over the last week from stored figures;
US CPI, a monthly figure, reads its latest month against the one before.

The chain's way is set by US CPI (rising: tightening, so rates, DXY and USD/VND up and gold down; falling: easing, the reverse); when CPI
is flat or missing, by US rates. Each other link is then "with" the chain, "against" it, "flat", or "missing". Descriptive only."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

WEEK = timedelta(days=7)
CPI_BAND, RATE_BAND = Decimal("0.1"), Decimal("0.10")             # percentage points
SHARE_BANDS = {"dxy": Decimal("0.005"), "gold": Decimal("0.01"), "usd_vnd": Decimal("0.002")}
STALE_DAYS = {"us_cpi": 75, "us_rates": 10, "dxy": 10, "gold": 10, "usd_vnd": 10}
RATE_PARTS = ("fed_effr", "us10y")
TIGHTENING = {"us_cpi": "up", "us_rates": "up", "dxy": "up", "gold": "down", "usd_vnd": "up"}

Points = list[tuple[date, Decimal]]


def _plain(v: Decimal) -> str:
    return "0" if v == 0 else format(v.normalize(), "f")


def _q(v: Decimal, places: str) -> str:
    return str(v.quantize(Decimal(places), ROUND_HALF_UP))


def _direction(change: Decimal, band: Decimal) -> str:
    return "up" if change > band else "down" if change < -band else "flat"


def _week_base(points: Points) -> tuple[tuple[date, Decimal], bool]:
    earlier = [p for p in points if p[0] <= points[-1][0] - WEEK]
    return (earlier[-1], False) if earlier else (points[0], True)


def _stale(points: Points, node: str, today: date) -> bool:
    return (today - points[-1][0]).days > STALE_DAYS[node]


def _missing(node: str) -> dict:
    return {"id": node, "direction": None, "latest": None, "stale": False}


def _cpi(head: Points, core: Points, today: date) -> dict:
    if not head:
        return _missing("us_cpi")
    out = {"id": "us_cpi", "latest": {"date": head[-1][0].isoformat(), "value": _plain(head[-1][1])}, "stale": _stale(head, "us_cpi", today),
           "direction": None, "change": None, "from": None}
    if len(head) > 1:
        change = head[-1][1] - head[-2][1]
        out.update(direction=_direction(change, CPI_BAND), change=_q(change, "0.01"), **{"from": head[-2][0].isoformat()})
    if core:
        out["core"] = {"date": core[-1][0].isoformat(), "value": _plain(core[-1][1]),
                       "change": _q(core[-1][1] - core[-2][1], "0.01") if len(core) > 1 else None}
    return out


def _rates(series: dict[str, Points], today: date) -> dict:
    parts = []
    for key in RATE_PARTS:
        points = series.get(key) or []
        if not points:
            continue
        (start, then), short = _week_base(points)
        change = points[-1][1] - then
        parts.append({"id": key, "direction": _direction(change, RATE_BAND) if len(points) > 1 else None,
                      "latest": {"date": points[-1][0].isoformat(), "value": _plain(points[-1][1])}, "from": start.isoformat(),
                      "change": _q(change, "0.01"), "short_history": short, "stale": _stale(points, "us_rates", today)})
    if not parts:
        return _missing("us_rates")
    moves = {p["direction"] for p in parts} - {"flat", None}
    return {"id": "us_rates", "direction": moves.pop() if len(moves) == 1 else "flat", "latest": None, "parts": parts,
            "short_history": any(p["short_history"] for p in parts), "stale": any(p["stale"] for p in parts)}


def _share(node: str, points: Points, today: date) -> dict:
    if not points:
        return _missing(node)
    (start, then), short = _week_base(points)
    change = points[-1][1] / then - 1 if then else Decimal(0)
    return {"id": node, "direction": _direction(change, SHARE_BANDS[node]) if len(points) > 1 else None,
            "latest": {"date": points[-1][0].isoformat(), "value": _plain(points[-1][1])}, "from": start.isoformat(),
            "change": _q(change, "0.0001"), "short_history": short, "stale": _stale(points, node, today)}


GRAMS_PER_OUNCE, GRAMS_PER_CHI = Decimal("31.1034768"), Decimal("3.75")


def gold_premium(*, xau: tuple[date, Decimal], usd_vnd: tuple[date, Decimal], sjc_sell: Decimal, sjc_as_of: str | None) -> dict:
    """Vàng miếng SJC's selling price against the world price turned into đồng a chỉ at the bank's USD selling rate (no tax or fee)."""
    world = xau[1] * usd_vnd[1] * GRAMS_PER_CHI / GRAMS_PER_OUNCE
    return {"world_per_chi": _q(world, "1"), "sjc_sell": _plain(sjc_sell), "gap": _q(sjc_sell - world, "1"), "gap_pct": _q(sjc_sell / world - 1, "0.0001"),
            "xau_date": xau[0].isoformat(), "fx_date": usd_vnd[0].isoformat(), "sjc_as_of": sjc_as_of}


SHORT = {"us_cpi": "CPI Mỹ", "us_rates": "lãi suất Mỹ", "dxy": "DXY", "gold": "vàng", "usd_vnd": "tỷ giá USD/VND"}
MOVE = {"up": "tăng", "down": "giảm", "flat": "đi ngang"}


def _vn(v: Decimal, places: int = 0) -> str:
    text = f"{abs(v):,.{places}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return ("−" if v < 0 else "") + text


def chain_summary(out: dict) -> str:
    """The same sentence as the page (us-chain.tsx chainSummary)."""
    if not out.get("mode") or not out.get("driver"):
        return "Tuần này CPI Mỹ và lãi suất Mỹ đều đi ngang: chuỗi chưa có chiều rõ."
    driver = next((n for n in out["nodes"] if n["id"] == out["driver"]), {})
    name = SHORT[out["driver"]]
    head = f"{name[0].upper()}{name[1:]} {MOVE.get(driver.get('direction') or 'flat')} nên chuỗi đang theo chiều "            f"{'thắt chặt' if out['mode'] == 'tightening' else 'nới lỏng'}."
    part = lambda label, ids: f" {label}: {', '.join(SHORT[i] for i in ids)}." if ids else ""  # noqa: E731
    return head + part("Khớp chuỗi", out["with"]) + part("Ngược chuỗi", out["against"]) + part("Đi ngang", out["flat"])         + part("Chưa có số", out["missing"])


def premium_text(p: dict) -> str:
    gap = Decimal(p["gap"])
    pct = Decimal(p["gap_pct"]) * 100
    return (f"Vàng miếng SJC bán ra {_vn(Decimal(p['sjc_sell']))} đ/chỉ, {'cao' if gap >= 0 else 'thấp'} hơn giá thế giới quy đổi "
            f"{_vn(Decimal(p['world_per_chi']))} đ/chỉ là {_vn(abs(gap))} đ ({'+' if pct > 0 else ''}{_vn(pct, 1)}%)")


def us_chain(series: dict[str, Points], *, today: date) -> dict:
    """series: us_cpi_yoy, us_core_cpi_yoy (monthly), fed_effr, us10y, dxy, gold (đồng per chỉ), usd_vnd_vcb, oldest first."""
    nodes = [_cpi(series.get("us_cpi_yoy") or [], series.get("us_core_cpi_yoy") or [], today), _rates(series, today),
             _share("dxy", series.get("dxy") or [], today), _share("gold", series.get("gold") or [], today),
             _share("usd_vnd", series.get("usd_vnd_vcb") or [], today)]
    driver = next((n for n in nodes[:2] if n["direction"] in ("up", "down")), None)
    mode = None if driver is None else "tightening" if driver["direction"] == TIGHTENING[driver["id"]] else "easing"
    for n in nodes:
        if n["latest"] is None and not n.get("parts"):
            n["fit"] = "missing"
        elif driver is not None and n["id"] == driver["id"]:
            n["fit"] = "driver"
        elif n["direction"] in (None, "flat"):
            n["fit"] = "flat"
        elif mode is None:
            n["fit"] = "none"
        else:
            expected = TIGHTENING[n["id"]] if mode == "tightening" else {"up": "down", "down": "up"}[TIGHTENING[n["id"]]]
            n["fit"] = "with" if n["direction"] == expected else "against"
    return {"mode": mode, "driver": driver["id"] if driver else None, "nodes": nodes,
            **{k: [n["id"] for n in nodes if n["fit"] == k] for k in ("with", "against", "flat", "missing")}}
