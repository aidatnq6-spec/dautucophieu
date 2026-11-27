"""Khối ngoại và tự doanh cùng chiều (owner, 27/11/2026, docs/superpowers/specs/2026-11-27-ngoai-tu-doanh-cung-chieu-design.md):
the core in đồng, shared by Bản tin (brief.flows.same_direction, tỷ đồng) and the public MCP tool cung_chieu. Public market data only."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from .foreign_history import ForeignStore
from .proprietary_history import ProprietaryStore

BARS = 20


TOP = 5


def _stock_nets(record: dict) -> dict[str, Decimal]:
    return {s: Decimal(f["buy_value"]) - Decimal(f["sell_value"]) for s, f in record["stocks"].items()}


def same_direction_raw(data_dir: Path, session_date: date, sessions: list[date], n: int = BARS, top: int = TOP) -> dict:
    """Over the n sessions ending at the newest one both stores have figures for (never after session_date), sessions either lacks
    dropped from both and counted; tickers both bought (or both sold) net, top by their combined net, as (symbol, foreign, tự doanh) in đồng."""
    foreign, proprietary = ForeignStore(data_dir), ProprietaryStore(data_dir)

    def nets(store, day: date) -> dict[str, Decimal] | None:
        try:
            record = store.read(day)
            return _stock_nets(record) if record and not record.get("thieu") else None
        except Exception:  # noqa: BLE001 - a damaged file is a missing session
            return None
    days = sorted({d for d in sessions if d <= session_date} | {session_date})
    both = {}
    for d in reversed(days[-(n + 60):]):
        f, p = nets(foreign, d), nets(proprietary, d)
        if f is not None and p is not None:
            both[d] = (f, p)
    if not both:
        return {"status": "missing", "reason": "Chưa có phiên nào cả khối ngoại và tự doanh đều có số"}
    newest = max(both)
    window = [d for d in days if d <= newest][-n:]
    kept = [both[d] for d in window if d in both]
    f_sum: dict[str, Decimal] = {}
    p_sum: dict[str, Decimal] = {}
    for f, p in kept:
        for s, v in f.items():
            f_sum[s] = f_sum.get(s, Decimal(0)) + v
        for s, v in p.items():
            p_sum[s] = p_sum.get(s, Decimal(0)) + v
    rows = [(s, f_sum[s], p_sum[s]) for s in f_sum if s in p_sum]
    pick = lambda xs: list(xs)[:top]  # noqa: E731
    return {"status": "ok", "from": window[0].isoformat(), "to": newest.isoformat(), "lag_sessions": sum(1 for d in days if d > newest),
            "dropped": len(window) - len(kept) + max(0, n - len(window)),
            "buy": pick(sorted((r for r in rows if r[1] > 0 and r[2] > 0), key=lambda r: (-(r[1] + r[2]), r[0]))),
            "sell": pick(sorted((r for r in rows if r[1] < 0 and r[2] < 0), key=lambda r: (r[1] + r[2], r[0])))}
