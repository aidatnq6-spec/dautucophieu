"""Whole-HOSE price board maths for the brief: breadth, matched value, foreign flows and sector moves.

Units as served by Vnstock's price board (checked 2026-10-26): prices in đồng, accumulated_value in million đồng
(matched orders only), foreign values in đồng. Rows of another trading day are never used.
"""

from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

OTHER = "Khác"
_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")


def _d(value) -> Decimal:
    try:
        return Decimal(str(value)) if value is not None else Decimal(0)
    except ArithmeticError:
        return Decimal(0)


def _s(value: Decimal, q: Decimal) -> str:
    return str(value.quantize(q, ROUND_HALF_UP))


def summarise_board(records: list[dict], *, session_date: date, icb_names: dict[str, str]) -> dict:
    rows = [r for r in records if str(r.get("trading_date") or "")[:10] == session_date.isoformat()]
    if not rows:
        return {"status": "missing", "reason": "Bảng giá chưa phải phiên này"}
    breadth = {"up": 0, "down": 0, "flat": 0, "no_trade": 0}
    value = volume = Decimal(0)
    fb_vol = fs_vol = 0
    fb_val = fs_val = Decimal(0)
    nets, groups, symbols = [], defaultdict(list), {}
    for r in rows:
        ref, price = _d(r.get("ref_price")), _d(r.get("match_price"))
        sector = icb_names.get(str(r.get("icb_code2") or ""), OTHER)
        traded = price > 0 and ref > 0
        pct = (price - ref) / ref if traded else None
        if not traded:
            breadth["no_trade"] += 1
        else:
            breadth["up" if price > ref else "down" if price < ref else "flat"] += 1
            groups[sector].append(pct)
        value += _d(r.get("accumulated_value"))
        volume += _d(r.get("accumulated_volume"))
        fb_vol += int(_d(r.get("foreign_buy_volume")))
        fs_vol += int(_d(r.get("foreign_sell_volume")))
        buy, sell = _d(r.get("foreign_buy_value")), _d(r.get("foreign_sell_value"))
        fb_val, fs_val = fb_val + buy, fs_val + sell
        if buy - sell != 0:
            nets.append((r["symbol"], buy - sell))
        symbols[r["symbol"]] = {"price": int(price) if traded else None, "ref": int(ref) if ref else None,
                                "change": int(price - ref) if traded else None, "pct": _s(pct, _Q4) if traded else None,
                                "sector": sector}
    bn = Decimal(1_000_000_000)
    top = lambda items: [{"symbol": s, "net_value_bn": _s(n / bn, _Q2)} for s, n in items[:3]]
    sectors = [{"sector": name, "pct": _s(sum(p) / len(p), _Q4), "count": len(p)} for name, p in groups.items()]
    sectors.sort(key=lambda x: (-Decimal(x["pct"]), x["sector"]))
    return {"status": "ok", "trading_date": session_date.isoformat(),
            "value_matched_bn": _s(value / 1000, _Q2), "volume_matched": int(volume), "breadth": breadth,
            "foreign": {"buy_volume": fb_vol, "sell_volume": fs_vol, "buy_value_bn": _s(fb_val / bn, _Q2),
                        "sell_value_bn": _s(fs_val / bn, _Q2), "net_value_bn": _s((fb_val - fs_val) / bn, _Q2),
                        "top_sell": top(sorted((x for x in nets if x[1] < 0), key=lambda x: x[1])),
                        "top_buy": top(sorted((x for x in nets if x[1] > 0), key=lambda x: -x[1]))},
            "sectors": sectors, "symbols": symbols}
