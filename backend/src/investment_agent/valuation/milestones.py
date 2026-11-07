"""Mốc giá quá khứ: today's price against the ticker's own past turning points, with the P/B and P/E each price would give on
today's figures. Facts about the past only: no time to reach a level, no odds, no pooled history of other tickers.

- Weekly closes: the last adjusted close of each week (thousand đồng in the store, đồng here); zero prices are skipped.
- Zigzag with the owner's threshold: a peak or trough is confirmed only once the price has moved the threshold away from it.
  The extreme of the leg still running is unconfirmed.
- Peak: the latest confirmed peak while the leg runs down, the running high while it runs up, the highest close if there is
  no turn yet. Corrections = each confirmed peak → the next confirmed trough; the running leg is not one.
- Only turning points from the first week of the P/B series on (today's P/B or P/E of a price from before the
  statements begin means nothing); older troughs below today are counted, not listed.
- Rows: today, every confirmed trough below today's close (and the running leg's low if lower than today), and the price at the
  lowest weekly P/B of the series (that P/B × today's equity per share). Each row: fall from the peak, P/B and P/E at that price
  on the latest week's figures (none when they are missing or not positive), gap to the lowest-P/B price, and how many past
  corrections went deeper than that fall.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .weekly import weekly_multiples

_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")
_ORDER = {"current": 0, "trough": 1, "low_now": 1, "pb_floor": 2}


def _r(value: Decimal | None, q: Decimal = _Q4) -> str | None:
    return None if value is None else str(value.quantize(q, ROUND_HALF_UP))


def _plain(value: Decimal) -> str:
    return format(value.quantize(Decimal(1), ROUND_HALF_UP).normalize(), "f")


def _month(day: date) -> str:
    return f"{day.month:02d}/{day.year}"


def weekly_closes(points) -> list[tuple[date, Decimal]]:
    weeks: dict[tuple[int, int], tuple[date, Decimal]] = {}
    for t, close in points:
        price = Decimal(str(close)) * 1000
        if price > 0:
            weeks[t.date().isocalendar()[:2]] = (t.date(), price)
    return [weeks[k] for k in sorted(weeks)]


def zigzag(closes: list[tuple[date, Decimal]], threshold: Decimal) -> dict:
    pivots: list[dict] = []
    if not closes:
        return {"pivots": pivots, "trend": None, "extreme": None}
    hi = lo = closes[0]
    trend, ext = None, None
    for d, p in closes[1:]:
        if trend is None:
            hi = (d, p) if p > hi[1] else hi
            lo = (d, p) if p < lo[1] else lo
            if hi[1] >= lo[1] * (1 + threshold):
                if lo[0] < hi[0]:
                    pivots.append({"kind": "trough", "date": lo[0], "price": lo[1]})
                    trend, ext = "up", hi
                else:
                    pivots.append({"kind": "peak", "date": hi[0], "price": hi[1]})
                    trend, ext = "down", lo
        elif trend == "up":
            if p > ext[1]:
                ext = (d, p)
            elif p <= ext[1] * (1 - threshold):
                pivots.append({"kind": "peak", "date": ext[0], "price": ext[1]})
                trend, ext = "down", (d, p)
        else:
            if p < ext[1]:
                ext = (d, p)
            elif p >= ext[1] * (1 + threshold):
                pivots.append({"kind": "trough", "date": ext[0], "price": ext[1]})
                trend, ext = "up", (d, p)
    return {"pivots": pivots, "trend": trend, "extreme": ext}


def _multiple(price: Decimal, shares: int | None, series: dict | None) -> Decimal | None:
    if not shares or not series or not series["points"]:
        return None
    d = Decimal(series["points"][-1]["denominator"])
    return (price * shares / d).quantize(_Q2, ROUND_HALF_UP) if d > 0 else None


def price_milestones(record: dict | None, points, *, today: date, threshold: Decimal, shares: int | None = None, published=None) -> dict:
    closes = weekly_closes(points)
    if not closes:
        return {"reason": "Chưa có lịch sử giá", "rows": [], "corrections": [], "floor": None, "threshold": _r(threshold)}
    zz = zigzag(closes, threshold)
    pivots, trend, ext = zz["pivots"], zz["trend"], zz["extreme"]
    day, close = closes[-1]
    if trend == "down":
        peak = (pivots[-1]["date"], pivots[-1]["price"])
    elif trend == "up":
        peak = ext
    else:
        peak = max(closes, key=lambda c: (c[1], c[0]))
    multiples = weekly_multiples(record, points, today=today, shares=shares, published=published)
    shares = multiples["shares"]
    pb_series = multiples["pb"] if multiples["reason"] is None else None
    pe_series = multiples["pe"] if multiples["reason"] is None else None
    # Today's P/B or P/E means nothing for a price from before the statements begin: list only what the P/B series covers.
    since = date.fromisoformat(pb_series["points"][0]["date"]) if pb_series and pb_series["points"] else None
    covered = [p for p in pivots if since is None or p["date"] >= since]
    corrections = [{"peak": a["date"].isoformat(), "trough": b["date"].isoformat(), "depth": _r(b["price"] / a["price"] - 1)}
                   for a, b in zip(pivots, pivots[1:]) if a["kind"] == "peak" and (since is None or a["date"] >= since)]
    floor = None
    known = [p for p in (pb_series or {"points": []})["points"] if p["value"] is not None]
    if known and shares:
        low = min(known, key=lambda p: (Decimal(p["value"]), p["date"]))
        equity = Decimal(pb_series["points"][-1]["denominator"])
        if equity > 0:
            floor = {"pb": low["value"], "date": low["date"], "price": _plain(Decimal(low["value"]) * equity / shares), "from": known[0]["date"]}

    def row(kind: str, label: str, when: date, price: Decimal) -> dict:
        drop = price / peak[1] - 1
        return {"kind": kind, "label": label, "date": when.isoformat(), "price": _plain(price), "drop": _r(drop),
                "pb": _r(_multiple(price, shares, pb_series), _Q2), "pe": _r(_multiple(price, shares, pe_series), _Q2),
                "vs_floor": _r(price / Decimal(floor["price"]) - 1) if floor else None,
                "deeper": sum(1 for c in corrections if Decimal(c["depth"]) < drop)}

    rows = [row("current", "Giá hiện tại", day, close)]
    rows += [row("trough", f"Đáy nhịp {_month(p['date'])}", p["date"], p["price"]) for p in covered if p["kind"] == "trough" and p["price"] < close]
    omitted = sum(1 for p in pivots if p["kind"] == "trough" and p["price"] < close and since is not None and p["date"] < since)
    if trend == "down" and ext[1] < close:
        rows.append(row("low_now", f"Đáy của nhịp đang giảm {_month(ext[0])} (chưa xác nhận)", ext[0], ext[1]))
    if floor:
        rows.append(row("pb_floor", f"Giá tại P/B thấp nhất từ {_month(date.fromisoformat(floor['from']))}",
                        date.fromisoformat(floor["date"]), Decimal(floor["price"])))
    rows.sort(key=lambda r: (-Decimal(r["price"]), _ORDER[r["kind"]]))
    return {"reason": None, "threshold": _r(threshold), "date": day.isoformat(), "close": _plain(close),
            "peak": {"date": peak[0].isoformat(), "price": _plain(peak[1])}, "drawdown": _r(close / peak[1] - 1),
            "trend": trend, "corrections": corrections, "floor": floor, "rows": rows, "weeks": len(closes), "from": closes[0][0].isoformat(),
            "since": since.isoformat() if since else None, "omitted_troughs": omitted}
