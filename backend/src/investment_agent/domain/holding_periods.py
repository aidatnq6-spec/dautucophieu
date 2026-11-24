"""Đợt nắm (a ticker from its first share to its last), and two views of them: Soi hình tháp khi mua thêm (where the money of later buys
went against the first buy's price) and Giỏ chiến lược (the owner's own baskets of periods, with what each made). Personal data,
computed on the owner's machine. Figures only; the pyramid label describes the shape of the buys and judges nothing.

Prices are compared on the adjusted series (a bonus issue between two buys must not look like a cheaper buy), and buys by the money put
in rather than by shares for the same reason. Realised gains are the ledger's own (moving-average cost, realised_sells)."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from investment_agent.domain.hindsight import _Series
from investment_agent.domain.ledger import OpeningBalance, Trade, ordered_events, realised_sells, replay, snapshots

MIN_PERIODS = 5
LABELS = ("upright", "inverted", "mixed")


def _r(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0001"), ROUND_HALF_UP), "f")


def _d(value: Decimal) -> str:
    return format(value.quantize(Decimal("1"), ROUND_HALF_UP), "f")


def _dmy(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def holding_periods(events) -> list[dict]:
    """Every period of every ticker in ledger order of their start: key "SYMBOL@start", start, end (None while held), whether the opening
    balance began it, its buys (day, money put in after fee and tax), its sells (day, proceeds after fee and tax, the cost the ledger released)
    and, for an open period, the shares and the cost held now."""
    ordered = ordered_events(list(events))
    released = {}
    open_: dict[str, dict] = {}
    out: list[dict] = []
    before: dict = {}
    for e, snap in snapshots(ordered):
        touched = set(snap) | set(before)
        if isinstance(e, OpeningBalance):
            for p in e.positions:
                open_[p.security_id] = {"symbol": p.security_id, "start": e.effective_at, "opening": True, "buys": [], "sells": []}
        elif isinstance(e, Trade):
            s = e.security_id
            if e.type == "buy":
                if s not in open_:
                    open_[s] = {"symbol": s, "start": e.effective_at, "opening": False, "buys": [], "sells": []}
                open_[s]["buys"].append({"on": e.effective_at.isoformat(), "outlay": _d(e.quantity * e.price + e.fee + e.tax)})
            else:
                if s not in released:
                    released[s] = iter(realised_sells(ordered, s))
                sale = next(released[s])
                open_[s]["sells"].append({"on": sale["on"], "proceeds": _d(Decimal(sale["proceeds"])), "cost": _d(Decimal(sale["cost"]))})
        for s in touched:
            shares = sum(snap[s][:2]) if s in snap else 0
            if shares <= 0 and s in open_:
                p = open_.pop(s)
                out.append({**p, "end": e.effective_at.isoformat()})
        before = snap
    state = {h.security_id: h for h in replay(ordered).positions}
    for s, p in open_.items():
        h = state.get(s)
        out.append({**p, "end": None, "shares": h.quantity + h.pending_quantity if h else 0, "cost": _d(h.total_cost) if h else "0"})
    out.sort(key=lambda p: (p["start"], p["symbol"]))
    return [{"key": f"{p['symbol']}@{p['start'].isoformat()}", **p, "start": p["start"].isoformat()} for p in out]


def _pyramid(p: dict, series: _Series) -> dict:
    row = {"key": p["key"], "symbol": p["symbol"], "start": p["start"], "end": p["end"], "label": None, "reason": None, "buys": [],
           "above_share": None, "largest": None, "mean_above": None, "mean_below": None}
    if p["opening"]:
        return {**row, "reason": "Đợt bắt đầu từ số dư đầu kỳ, không có lần mua đầu để so"}
    closes = []
    for b in p["buys"]:
        got = series.on(date.fromisoformat(b["on"]))
        if got is None:
            return {**row, "reason": f"Chưa có giá đã lưu tại ngày mua {_dmy(date.fromisoformat(b['on']))}"}
        closes.append(got[1])
    levels = [c / closes[0] - 1 for c in closes]
    money = [Decimal(b["outlay"]) for b in p["buys"]]
    buys = [{**b, "level": _r(lv)} for b, lv in zip(p["buys"], levels)]
    largest = max(range(len(money)), key=lambda i: (money[i], -i))
    lowest = min(range(len(levels)), key=lambda i: (levels[i], i))
    highest = max(range(len(levels)), key=lambda i: (levels[i], -i))
    label = "upright" if largest == lowest else "inverted" if largest == highest and levels[largest] > 0 else "mixed"
    above = [m for m, lv in zip(money, levels) if lv > 0]
    below = [m for m, lv in zip(money, levels) if lv <= 0]
    return {**row, "label": label, "buys": buys, "above_share": _r(sum(above, Decimal(0)) / sum(money)), "largest": buys[largest],
            "mean_above": _d(sum(above) / len(above)) if above else None, "mean_below": _d(sum(below) / len(below)) if below else None}


def pyramids(periods: list[dict], *, closes: dict, today: date) -> dict:
    """Periods with at least two buys (an opening balance counts as the first), newest first; the label counts, and the mean share put in
    above the first buy only from five compared periods."""
    series = {s: _Series(p, today, 1000) for s, p in closes.items()}
    empty = _Series([], today, 1000)
    rows = [_pyramid(p, series.get(p["symbol"], empty)) for p in periods if len(p["buys"]) + p["opening"] >= 2]
    rows.sort(key=lambda r: r["start"], reverse=True)
    compared = [r for r in rows if r["label"]]
    enough = len(compared) >= MIN_PERIODS
    return {"rows": rows, "summary": {"counts": {k: sum(r["label"] == k for r in compared) for k in LABELS}, "compared": len(compared),
                                      "mean_above_share": _r(sum(Decimal(r["above_share"]) for r in compared) / len(compared)) if enough else None,
                                      "enough": enough}}


def _days_held(p: dict) -> int:
    return (date.fromisoformat(p["end"]) - date.fromisoformat(p["start"])).days


def basket_view(periods: list[dict], baskets: dict, *, prices: dict[str, Decimal]) -> dict:
    """baskets: {baskets: [{id, name}], tags: {period key: basket id}}; prices: last price per share in đồng. One row per basket and one for
    the untagged periods; tags that no longer match a period are listed so they can be set again."""
    tags, keys = baskets.get("tags", {}), {p["key"] for p in periods}
    known = {b["id"] for b in baskets.get("baskets", [])}
    rows = []
    for basket in [*baskets.get("baskets", []), {"id": None, "name": None}]:
        mine = [p for p in periods if (tags.get(p["key"]) if tags.get(p["key"]) in known else None) == basket["id"]]
        sells = [s for p in mine for s in p["sells"]]
        realised = sum((Decimal(s["proceeds"]) - Decimal(s["cost"]) for s in sells), Decimal(0))
        released = sum((Decimal(s["cost"]) for s in sells), Decimal(0))
        closed, held = [p for p in mine if p["end"]], [p for p in mine if not p["end"]]
        enough = len(closed) >= MIN_PERIODS
        wins = sum(sum(Decimal(s["proceeds"]) - Decimal(s["cost"]) for s in p["sells"]) > 0 for p in closed)
        missing = sorted({p["symbol"] for p in held if prices.get(p["symbol"]) is None})
        open_cost = sum((Decimal(p["cost"]) for p in held), Decimal(0))
        value = sum((p["shares"] * prices[p["symbol"]] for p in held if prices.get(p["symbol"]) is not None), Decimal(0))
        rows.append({"id": basket["id"], "name": basket["name"], "closed": len(closed), "open": len(held),
                     "realised": _d(realised), "released": _d(released), "realised_ratio": _r(realised / released) if released else None,
                     "win_rate": _r(Decimal(wins) / len(closed)) if enough else None,
                     "mean_days": format((Decimal(sum(_days_held(p) for p in closed)) / len(closed)).quantize(Decimal("0.1"), ROUND_HALF_UP), "f") if enough else None,
                     "enough": enough, "open_cost": _d(open_cost), "unrealised": None if missing or not held else _d(value - open_cost), "missing": missing})
    view = [{"key": p["key"], "symbol": p["symbol"], "start": p["start"], "end": p["end"],
             "basket": tags.get(p["key"]) if tags.get(p["key"]) in known else None} for p in periods]
    return {"rows": rows, "periods": view, "stale": sorted(k for k in tags if k not in keys)}
