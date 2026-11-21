"""Reads the stored public data for Dòng tiền & kỹ thuật (Theo dõi) and Hiệu suất theo kỳ (Chuỗi giá trị): closes from
data/trend-sources, daily bars from the price store, each ticker's foreign net from the session snapshots (data/brief). The held tickers
only order the rows and mark them on the page; nothing is sent anywhere."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from investment_agent.domain.chain_returns import chain_returns
from investment_agent.domain.flow_board import flag_counts, stock_row
from investment_agent.market.series import SeriesStore

SNAPSHOTS = 30  # the session snapshots read for the foreign run (more than enough for a run of five)


def _closes(data_dir: Path, symbol: str) -> list[tuple[date, Decimal]]:
    return [(t.date(), Decimal(str(v))) for t, v in SeriesStore(Path(data_dir) / "trend-sources").read(f"{symbol}-1d")]


def stored_bars(data_dir: Path, store=None):
    """bars(symbol) from the price store: the app's own when given (its views are kept warm by the other pages), else one shared per
    data folder. The first read of every ticker's revisions takes about two seconds; later ones reuse the merged views."""
    from investment_agent.services.deposit_book import _PRICE_STORES
    from investment_agent.market.prices import PriceStore
    if store is None:
        if not (Path(data_dir) / "prices").exists():
            return lambda symbol: []
        root = Path(data_dir).resolve()
        store = _PRICE_STORES.setdefault(root, PriceStore(root))

    def bars(symbol):
        view = store.latest(symbol)
        return [(d, view[d][0].high, view[d][0].low, view[d][0].close, view[d][0].volume) for d in sorted(view)]
    return bars


def _foreign(data_dir: Path) -> dict[str, list[tuple[date, Decimal]]]:
    """Each ticker's foreign net (tỷ đồng) per stored session snapshot, oldest first; a snapshot without the figure is skipped."""
    root, out = Path(data_dir) / "brief", {}
    files = sorted(root.glob("????-??-??.json"))[-SNAPSHOTS:] if root.is_dir() else []
    for f in files:
        try:
            symbols = (json.loads(f.read_text(encoding="utf-8")).get("board") or {}).get("symbols") or {}
        except (OSError, ValueError):
            continue
        day = date.fromisoformat(f.stem)
        for s, row in symbols.items():
            if isinstance(row, dict) and row.get("foreign_net_bn") not in (None, ""):
                out.setdefault(s, []).append((day, Decimal(str(row["foreign_net_bn"]))))
    return out


def flow_board(data_dir: Path, symbols: list[str], *, held: set[str], bars_for=None) -> dict:
    bars_for = bars_for or stored_bars(data_dir)
    foreign = _foreign(data_dir)
    rows = [stock_row(s, closes=_closes(data_dir, s), bars=bars_for(s), foreign=foreign.get(s, []), held=s in held) for s in symbols]
    ratio = lambda r: Decimal(r["volume_ratio"]) if r["volume_ratio"] else Decimal(-1)  # noqa: E731
    rows.sort(key=lambda r: (not r["held"], -ratio(r), r["symbol"]))
    dates = [r["date"] for r in rows if r["date"]]
    return {"date": max(dates) if dates else None, "rows": rows, "counts": flag_counts(rows), "basis": "closes"}


def chain_board(data_dir: Path, chains: list[dict], *, today: date) -> list[dict]:
    symbols = {s for c in chains for s in c["symbols"]}
    return chain_returns(chains, {s: _closes(data_dir, s) for s in symbols}, today=today)
