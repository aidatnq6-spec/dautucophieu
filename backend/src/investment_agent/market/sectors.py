"""Market and sector view from stored prices only: VN-Index, breadth and ICB sector moves.

Sector figures are equal-weighted averages over the watched tickers (no market
caps in the free source), so they describe this watchlist, not the official
sector indices. No valuation, no macro data, no recommendations.
"""

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .watchlist import LOOKBACK

SECTORS_FILE, INDEX = "industries.json", "VNINDEX"
UNCLASSIFIED = "Chưa phân ngành"
_Q4, _Q2 = Decimal("0.0001"), Decimal("0.01")


def load_sectors(data_dir: Path | None) -> tuple[dict[str, str], str | None]:
    path = Path(data_dir) / SECTORS_FILE if data_dir is not None else None
    if path is None or not path.is_file():
        return {}, None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return dict(raw["sectors"]), raw.get("as_of")


def _mean(values: list[Decimal]) -> str | None:
    return str((sum(values) / len(values)).quantize(_Q4, ROUND_HALF_UP)) if values else None


def breadth(rows: list[dict]) -> dict[str, int]:
    moves = [Decimal(r["change_1d"]) for r in rows if r["change_1d"] is not None]
    return {"up": sum(m > 0 for m in moves), "down": sum(m < 0 for m in moves), "flat": sum(m == 0 for m in moves),
            "missing": len(rows) - len(moves)}


def sector_rows(rows: list[dict], sectors: dict[str, str]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(sectors.get(r["ticker"], UNCLASSIFIED), []).append(r)
    result = []
    for name, members in groups.items():
        d1 = [Decimal(r["change_1d"]) for r in members if r["change_1d"] is not None]
        ranked = sorted((r for r in members if r["change_20d"] is not None), key=lambda r: Decimal(r["change_20d"]))
        result.append({"sector": name, "count": len(members), "tickers": [r["ticker"] for r in members],
                       "avg_1d": _mean(d1), "avg_20d": _mean([Decimal(r["change_20d"]) for r in ranked]),
                       **breadth(members), "best": ranked[-1]["ticker"] if ranked else None, "worst": ranked[0]["ticker"] if ranked else None,
                       "held": [r["ticker"] for r in members if r["held"]]})
    # Strongest over 20 sessions first; sectors without that figure last.
    return sorted(result, key=lambda s: (s["avg_20d"] is None, -Decimal(s["avg_20d"] or 0), s["sector"]))


def index_summary(market, entity_id: str = INDEX) -> dict | None:
    history = market.recent_closes(entity_id, LOOKBACK + 1) if hasattr(market, "recent_closes") else []
    if not history:
        return None
    last = history[-1]
    window = [p.price for p in history[-LOOKBACK:]]

    def change(old):
        return str((last.price / old - 1).quantize(_Q4, ROUND_HALF_UP))

    ma = (sum(window) / len(window)).quantize(_Q2, ROUND_HALF_UP) if len(window) == LOOKBACK else None
    return {"entity_id": entity_id, "close": str(last.price), "date": last.session_date.isoformat(),
            "change_1d": change(history[-2].price) if len(history) >= 2 else None,
            "change_20d": change(history[0].price) if len(history) > LOOKBACK else None,
            "ma20": str(ma) if ma is not None else None, "above_ma20": last.price > ma if ma is not None else None}
