"""Tín hiệu phiên: what the session's headline figures hide.

- Mã kéo chỉ số: each stock's points on VN-Index, from its price change and the shares VNDirect lists (ratio OUTSTANDING_SHARES), on the
  index's own arithmetic (points = previous close × change in cap / cap at reference). Shown only when the points add up to the index's
  real move (within 0.5 point or 10%): VN-Index counts listed shares, VNDirect outstanding ones, and a gap beyond that is said, not shown.
- Xanh vỏ đỏ lòng: the index up while one and a half times as many stocks fall as rise (and the other way round).
- Thanh khoản thấp: matched volume under 80% of its 20-session average, with how many sessions in a row it has been under the average.
"""

from decimal import ROUND_HALF_UP, Decimal

TOP, WITHOUT = 5, 3
GAP = Decimal("1.5")
LOW = Decimal("0.8")
_Q2 = Decimal("0.01")


def _s(v: Decimal) -> str:
    return str(v.quantize(_Q2, ROUND_HALF_UP))


def index_pull(symbols: dict, shares: dict, *, change: Decimal, close: Decimal) -> dict:
    priced = {s: r for s, r in symbols.items() if r.get("ref") and s in shares}
    if not priced:
        return {"status": "missing", "reason": "Chưa có số cổ phiếu lưu hành của các mã"}
    cap = sum(Decimal(r["ref"]) * shares[s] for s, r in priced.items())
    previous = close - change
    points = {s: previous * Decimal(r["change"]) * shares[s] / cap for s, r in priced.items() if r.get("change")}
    computed = sum(points.values(), Decimal(0))
    if abs(computed - change) > max(Decimal("0.5"), abs(change) / 10):
        return {"status": "mismatch", "computed": _s(computed), "actual": _s(change),
                "reason": "Tổng điểm tính theo vốn hóa lệch quá xa mức thay đổi của VN-Index"}
    up = sorted(((s, p) for s, p in points.items() if p > 0), key=lambda x: -x[1])
    down = sorted(((s, p) for s, p in points.items() if p < 0), key=lambda x: x[1])
    lead = (up if change >= 0 else down)[:WITHOUT]
    return {"status": "ok", "computed": _s(computed), "actual": _s(change),
            "up": [{"symbol": s, "points": _s(p)} for s, p in up[:TOP]], "down": [{"symbol": s, "points": _s(p)} for s, p in down[:TOP]],
            "without_top": {"symbols": [s for s, _ in lead], "points": _s(change - sum((p for _, p in lead), Decimal(0)))} if lead else None}


def session_signals(*, index_change: Decimal | None, breadth: dict | None, volume: dict | None, earlier_ratios: list) -> dict:
    """earlier_ratios: the matched-volume ratio to its 20-session average of the sessions before, oldest first (None when unknown)."""
    gap = None
    if index_change is not None and breadth:
        up, down = breadth["up"], breadth["down"]
        if index_change > 0 and down >= GAP * up and down > up:
            gap = {"kind": "green_over_red", "up": up, "down": down}
        elif index_change < 0 and up >= GAP * down and up > down:
            gap = {"kind": "red_over_green", "up": up, "down": down}
    liquidity = None
    if volume and volume.get("status") == "ok" and volume.get("ratio20") is not None:
        ratio = Decimal(volume["ratio20"])
        run = 0
        if ratio < 1:
            run = 1
            for r in reversed(earlier_ratios):
                if r is None or r >= 1:
                    break
                run += 1
        liquidity = {"ratio20": volume["ratio20"], "change_pct": volume.get("change_pct"), "low": ratio < LOW, "below_avg_sessions": run}
    return {"breadth_gap": gap, "liquidity": liquidity}
