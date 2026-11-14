"""Price-only watchlist: the tickers in data/market-symbols.txt with their index groups.

It shows stored closes and their changes, never recommendations: tickers enter
the research universe only through verified audits (see universe.py).
"""

import json
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

SYMBOLS_FILE, GROUPS_FILE = "market-symbols.txt", "index-groups.json"
LOOKBACK = 20  # sessions, about one month


@dataclass(frozen=True)
class Watchlist:
    symbols: tuple[str, ...] = ()
    groups: dict[str, tuple[str, ...]] = field(default_factory=dict)
    groups_as_of: str | None = None
    group_dates: dict[str, str] = field(default_factory=dict)  # each group's own date: a kept group's is the day it was taken
    kept: tuple[str, ...] = ()  # groups without a public source, kept as last taken
    vn30_changed_on: str | None = None


def load_watchlist(data_dir: Path | None) -> Watchlist:
    if data_dir is None or not (Path(data_dir) / SYMBOLS_FILE).is_file():
        return Watchlist()
    data_dir = Path(data_dir)
    symbols = []
    for line in (data_dir / SYMBOLS_FILE).read_text(encoding="utf-8").splitlines():
        s = line.strip().upper()
        if s and s not in symbols:
            symbols.append(s)
    groups, as_of, raw = {}, None, {}
    if (data_dir / GROUPS_FILE).is_file():
        raw = json.loads((data_dir / GROUPS_FILE).read_text(encoding="utf-8"))
        groups, as_of = {g: tuple(m) for g, m in raw["groups"].items()}, raw.get("as_of")
    kept = raw.get("kept") or {}
    dates = {g: kept.get(g) or as_of for g in groups if kept.get(g) or as_of}
    return Watchlist(tuple(symbols), groups, as_of, dates, tuple(sorted(kept)), raw.get("vn30_changed_on"))


def vn100_review(watchlist: Watchlist) -> dict | None:
    """VN30 changed after the kept VN100 list was taken: HOSE reviewed its baskets, so VN100 may be out of date."""
    kept_on = watchlist.group_dates.get("VN100") if "VN100" in watchlist.kept else None
    changed = watchlist.vn30_changed_on
    return {"vn30_changed_on": changed, "vn100_as_of": kept_on} if kept_on and changed and changed > kept_on else None


def _change(new: Decimal, old: Decimal) -> str:
    return str((new / old - 1).quantize(Decimal("0.0001"), ROUND_HALF_UP))


def watchlist_rows(market, watchlist: Watchlist, *, held: set[str]) -> list[dict]:
    rows = []
    for ticker in watchlist.symbols:
        history = market.recent_closes(ticker, LOOKBACK + 1) if hasattr(market, "recent_closes") else []
        last = history[-1] if history else None
        rows.append({
            "ticker": ticker, "groups": [g for g, members in watchlist.groups.items() if ticker in members], "held": ticker in held,
            "close": str(last.price) if last else None, "date": last.session_date.isoformat() if last else None,
            "change_1d": _change(last.price, history[-2].price) if len(history) >= 2 else None,
            "change_20d": _change(last.price, history[0].price) if len(history) > LOOKBACK else None,
            # Shown with its date, but older than the market's freshness limit: not today's picture.
            "stale": last is not None and market.price(ticker) is None,
        })
    return rows
