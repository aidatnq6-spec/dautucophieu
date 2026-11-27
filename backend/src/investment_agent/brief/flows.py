"""Khối ngoại và tự doanh ròng 20 phiên on Bản tin (owner, 27/11/2026, docs/superpowers/specs/2026-11-27-ngoai-tu-doanh-20-phien-design.md).

Each row ends at the newest session its store has figures for, never after the brief's session, with how many sessions it lags. Foreign
net is the sum over the session's stocks (as the brief's Khối ngoại line); tự doanh net is VNDirect's VNINDEX row. A session without
figures is a blank bar (None), never 0, and is counted.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from investment_agent.market.foreign_history import ForeignStore
from investment_agent.market.proprietary_history import ProprietaryStore

BARS = 20
_BN, _Q2 = Decimal(1_000_000_000), Decimal("0.01")


def _bn(value: Decimal) -> str:
    return str((value / _BN).quantize(_Q2, ROUND_HALF_UP))


def _foreign_net(record: dict) -> Decimal:
    return sum((Decimal(s["buy_value"]) - Decimal(s["sell_value"]) for s in record["stocks"].values()), Decimal(0))


def _proprietary_net(record: dict) -> Decimal:
    return Decimal(record["index"]["buy_value"]) - Decimal(record["index"]["sell_value"])


def _flow(store, net, *, session_date: date, sessions: list[date], n: int, empty: str) -> dict:
    def figure(day: date) -> Decimal | None:
        """The session's net, None when it has no figures or its file cannot be read (that session only)."""
        try:
            record = store.read(day)
            return net(record) if record and not record.get("thieu") else None
        except Exception:  # noqa: BLE001 - a damaged file blanks its own session, never the row or the other row
            return None
    days = sorted({d for d in sessions if d <= session_date} | {session_date})  # the brief's session counts even if the calendar lacks it
    nets_by_day = {d: figure(d) for d in days[-(n + 60):]}
    newest = next((d for d in reversed(days) if nets_by_day.get(d) is not None), None)
    if newest is None:
        return {"status": "missing", "reason": empty}
    window = [d for d in days if d <= newest][-n:]
    nets = [nets_by_day.get(d) for d in window]
    known = [v for v in nets if v is not None]
    return {"status": "ok", "date": newest.isoformat(), "lag_sessions": sum(1 for d in days if d > newest), "net_bn": _bn(nets[-1]),
            "sum_bn": _bn(sum(known, Decimal(0))), "missing": len(nets) - len(known),
            "bars": [{"date": d.isoformat(), "net_bn": None if v is None else _bn(v)} for d, v in zip(window, nets)]}


def net_flows(data_dir: Path, session_date: date, sessions: list[date], n: int = BARS) -> dict:
    """sessions: HOSE sessions up to session_date (any order, at least n + the lag)."""
    return {"foreign": _flow(ForeignStore(data_dir), _foreign_net, session_date=session_date, sessions=sessions, n=n,
                             empty="Chưa có số khối ngoại theo phiên (foreign-sync chạy ở lượt 20:00)"),
            "proprietary": _flow(ProprietaryStore(data_dir), _proprietary_net, session_date=session_date, sessions=sessions, n=n,
                                 empty="Chưa có số tự doanh theo phiên (proprietary-sync chạy ở lượt 20:00)")}


TOP = 5


def _stock_nets(record: dict) -> dict[str, Decimal]:
    return {s: Decimal(f["buy_value"]) - Decimal(f["sell_value"]) for s, f in record["stocks"].items()}


def same_direction(data_dir: Path, session_date: date, sessions: list[date], n: int = BARS, top: int = TOP) -> dict:
    """Khối ngoại và tự doanh cùng chiều (owner, 27/11/2026): over the n sessions ending at the newest one both stores have figures for,
    sessions either lacks dropped from both and counted; tickers both bought (or both sold) net, top by their combined net."""
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
    pick = lambda xs: [{"symbol": s, "foreign_bn": _bn(f), "proprietary_bn": _bn(p)} for s, f, p in xs[:top]]  # noqa: E731
    return {"status": "ok", "from": window[0].isoformat(), "to": newest.isoformat(), "lag_sessions": sum(1 for d in days if d > newest),
            "dropped": len(window) - len(kept) + max(0, n - len(window)),
            "buy": pick(sorted((r for r in rows if r[1] > 0 and r[2] > 0), key=lambda r: (-(r[1] + r[2]), r[0]))),
            "sell": pick(sorted((r for r in rows if r[1] < 0 and r[2] < 0), key=lambda r: (r[1] + r[2], r[0])))}
