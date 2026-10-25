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


def load_watchlist(data_dir: Path | None) -> Watchlist:
    if data_dir is None or not (Path(data_dir) / SYMBOLS_FILE).is_file():
        return Watchlist()
    data_dir = Path(data_dir)
    symbols = []
    for line in (data_dir / SYMBOLS_FILE).read_text(encoding="utf-8").splitlines():
        s = line.strip().upper()
        if s and s not in symbols:
            symbols.append(s)
    groups, as_of = {}, None
    if (data_dir / GROUPS_FILE).is_file():
        raw = json.loads((data_dir / GROUPS_FILE).read_text(encoding="utf-8"))
        groups, as_of = {g: tuple(m) for g, m in raw["groups"].items()}, raw.get("as_of")
    return Watchlist(tuple(symbols), groups, as_of)


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
