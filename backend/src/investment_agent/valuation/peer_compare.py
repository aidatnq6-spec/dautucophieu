"""So sánh cùng ngành: the watched tickers of one sector side by side, one row each, at one quarter.

Every figure is one the ticker's own page already shows (Bảng số tài chính, Chỉ số ngành, Định giá); nothing is estimated. The
quarter is the latest one every ticker with data has, unless the owner picks another; a ticker without that quarter is left
blank with the reason, never filled from another quarter. Each ranked column marks its best and worst in its own direction
(lower P/E, lower NPL, higher ROE…) and gives the median; a ticker counts the columns where it is in the best third. There is
deliberately no overall score: weighting the columns would be the application's opinion.
"""

import math
from decimal import Decimal

# key, label, format (money, x, pct, pct2, score), better ("high", "low", None: not ranked), scope ("q": the quarter,
# "year": the last year end before it, "now": today's valuation board).
_HEAD = [("market_cap", "Vốn hoá", "money", None, "q"), ("pb", "P/B", "x", "low", "q"), ("pe", "P/E", "x", "low", "q"),
         ("roe", "ROE", "pct", "high", "q")]
_NOW = [("quality", "Điểm sức khỏe", "score", "high", "now"), ("gap", "Giá so với giá hợp lý", "pct", "low", "now")]
COLUMNS = {
    None: [("market_cap", "Vốn hoá", "money", None, "q"), ("pe", "P/E", "x", "low", "q"), ("pb", "P/B", "x", "low", "q"),
           ("ev_ebitda", "EV/EBITDA", "x", "low", "q"), ("roe", "ROE", "pct", "high", "q"), ("gross_margin", "Biên gộp", "pct", "high", "q"),
           ("revenue_yoy", "Doanh thu so cùng kỳ", "pct", "high", "q"), ("npat_parent_yoy", "LNST mẹ so cùng kỳ", "pct", "high", "q"),
           ("debt_to_equity", "Vay / vốn chủ", "x", "low", "q"),
           ("quality", "F-Score", "score", "high", "now"), ("gap", "Giá so với giá hợp lý", "pct", "low", "now")],
    "bank": _HEAD + [("ROAA_TR_AVG4Q", "ROAA", "pct2", "high", "q"), ("NET_INTEREST_MARGIN_TR_AVG5Q", "NIM", "pct2", "high", "q"),
                     ("BAD_LOANS_RATIO_AQ", "NPL", "pct2", "low", "q"), ("GROUP2_RATIO", "Nợ nhóm 2", "pct2", "low", "q"),
                     ("PROVISION_BAD_LOANS_AQ", "Bao phủ nợ xấu", "pct", "high", "q"), ("CASA", "CASA", "pct", "high", "q"),
                     ("LOANS_TO_DEPOSIT_AQ", "LDR", "pct", None, "q"), ("CUSTOMER_LOANS_AQ_GRYOY", "Tăng trưởng cho vay", "pct", "high", "q"),
                     ("CAR", "CAR cuối năm", "pct2", "high", "year")] + _NOW,
    "securities": _HEAD + [("ROAA_TR_AVG4Q", "ROAA", "pct2", "high", "q"), ("NET_MARGIN_TR", "Biên lợi nhuận ròng", "pct", "high", "q"),
                           ("LOANS_TO_EQUITY_AQ", "Cho vay / vốn chủ", "x", "low", "q")] + _NOW,
    "insurance": _HEAD + [("ROAA_TR_AVG4Q", "ROAA", "pct2", "high", "q"), ("COMBINED_RATIO_TR", "Tỷ lệ kết hợp", "pct", "low", "q"),
                          ("NET_MARGIN_TR", "Biên lợi nhuận ròng", "pct", "high", "q")] + _NOW,
}


def _label(period: str) -> str:
    return f"Q{period[-1]}/{period[:4]}"


def _number(value: str | None, fmt: str) -> Decimal | None:
    if value is None:
        return None
    if fmt == "score":
        score, _, of = value.partition("/")
        return Decimal(score) / Decimal(of) if of and Decimal(of) > 0 else None
    return Decimal(value)


def _year_end(period: str) -> str:
    """The last year end at or before the quarter: its own year for Q4, the year before otherwise."""
    return period[:4] if period.endswith("Q4") else str(int(period[:4]) - 1)


def compare(kind: str | None, peers: dict[str, dict[str, dict[str, str | None]]], now: dict[str, dict], *, focus: str,
            period: str | None = None) -> dict:
    """`peers`: {ticker: {"2026-Q3": {key: value}}} (the year-end CAR under its Q4); `now`: {ticker: {"quality": "6/9", "gap": "…"}}."""
    columns = COLUMNS[kind]
    quarterly = [c[0] for c in columns if c[4] == "q"]

    def has_quarter(values: dict) -> bool:
        return any(values.get(k) is not None for k in quarterly)
    latest = {s: max((p for p, v in rows.items() if has_quarter(v)), default=None) for s, rows in peers.items()}
    counts: dict[str, int] = {}
    for rows in peers.values():
        for p, v in rows.items():
            if has_quarter(v):
                counts[p] = counts.get(p, 0) + 1
    periods = sorted((p for p, n in counts.items() if n >= 2), reverse=True)
    default = min((p for p in latest.values() if p), default=None)
    period = period if period in periods else default

    rows = []
    for symbol in sorted(peers):
        data = peers[symbol]
        here = data.get(period, {}) if period else {}
        values = {}
        for key, _, _, _, scope in columns:
            values[key] = (now.get(symbol, {}).get(key) if scope == "now"
                           else (data.get(f"{_year_end(period)}-Q4", {}).get(key) if period else None) if scope == "year"
                           else here.get(key))
        reason = ("Chưa có số liệu (đồng bộ lúc 20:00)" if latest[symbol] is None
                  else f"Chưa có số {_label(period)}" if period and not has_quarter(here) else None)
        rows.append({"symbol": symbol, "values": values, "reason": reason, "top": 0})

    best, worst, median, ranked = {}, {}, {}, 0
    for key, _, fmt, better, _ in columns:
        found = [(r["symbol"], n) for r in rows if (n := _number(r["values"][key], fmt)) is not None]
        if found and fmt != "score":
            ordered = sorted(n for _, n in found)
            mid = len(ordered) // 2
            m = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
            median[key] = format(m.quantize(Decimal("0.01") if fmt == "x" else Decimal(1) if fmt == "money" else Decimal("0.0001")), "f")
        if better is None or len(found) < 2:
            continue
        ranked += 1
        ordered = sorted(found, key=lambda x: x[1], reverse=better == "high")
        best[key] = [s for s, n in ordered if n == ordered[0][1]]
        worst[key] = [s for s, n in ordered if n == ordered[-1][1]]
        cut = ordered[math.ceil(len(ordered) / 3) - 1][1]
        for r in rows:
            n = _number(r["values"][key], fmt)
            if n is not None and (n >= cut if better == "high" else n <= cut):
                r["top"] += 1
    return {"kind": kind, "focus": focus, "period": period, "periods": periods, "car_year": _year_end(period) if period else None,
            "columns": [{"key": k, "label": label, "format": fmt, "better": better, "scope": scope} for k, label, fmt, better, scope in columns],
            "rows": rows, "best": best, "worst": worst, "median": median, "ranked": ranked}
