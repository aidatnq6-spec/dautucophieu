"""Tự doanh for the brief: proprietary trading on HOSE from VNDirect's public v4/proprietary_trading (owner, 27/11/2026).

VNDirect posts these some sessions late and misses a few sessions (19 of 319 from 13/8/2025 to 23/11/2026), so the section is
always the latest session VNDirect has, up to the brief's own, shown with its date and how many sessions it lags. Another
session is never passed off as the brief's. Totals are VNDirect's VNINDEX row; the three strongest net buys and sells come from
that session's tickers, only when the tickers add up to the VNINDEX row. Values in đồng as served.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

_BN, _Q2 = Decimal(1_000_000_000), Decimal("0.01")


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def _bn(value: Decimal) -> str:
    return str((value / _BN).quantize(_Q2, ROUND_HALF_UP))


def summarise_proprietary(index_row: dict | None, stocks: list[dict], *, session_date: date, sessions: list[date]) -> dict:
    """sessions: the calendar's sessions up to and including session_date, ascending (the ones the brief keeps)."""
    if not index_row or not index_row.get("date"):
        return {"status": "missing", "reason": "VNDirect chưa có số tự doanh"}
    day = date.fromisoformat(str(index_row["date"])[:10])
    if day > session_date or not sessions or day < sessions[0]:
        return {"status": "missing", "reason": f"Số tự doanh gần nhất của VNDirect là phiên {day:%d/%m/%Y}, quá cũ"}
    buy, sell = _d(index_row.get("buyingVal")), _d(index_row.get("sellingVal"))
    rows = [r for r in stocks if str(r.get("date"))[:10] == day.isoformat() and r.get("type") == "STOCK" and r.get("floor") == "HOSE"]
    adds_up = bool(rows) and (sum(_d(r.get("buyingVal")) for r in rows), sum(_d(r.get("sellingVal")) for r in rows)) == (buy, sell)
    out = {"status": "ok", "source": "VNDirect", "date": day.isoformat(), "lag_sessions": sum(1 for s in sessions if day < s <= session_date),
           "buy_volume": int(_d(index_row.get("buyingVol"))), "sell_volume": int(_d(index_row.get("sellingVol"))),
           "buy_value_bn": _bn(buy), "sell_value_bn": _bn(sell), "net_value_bn": _bn(buy - sell)}
    if not adds_up:
        return {**out, "top_buy": None, "top_sell": None, "top_reason": "Tổng các mã không khớp dòng tổng VN-Index của VNDirect"}
    nets = [(str(r["code"]).upper(), _d(r.get("buyingVal")) - _d(r.get("sellingVal"))) for r in rows if r.get("code")]
    top = lambda items: [{"symbol": s, "net_value_bn": _bn(n)} for s, n in items[:3]]  # noqa: E731
    return {**out, "top_buy": top(sorted((x for x in nets if x[1] > 0), key=lambda x: -x[1])),
            "top_sell": top(sorted((x for x in nets if x[1] < 0), key=lambda x: x[1]))}
