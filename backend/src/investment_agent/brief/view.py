"""Brief market section as shown: the public snapshot plus local, personal ordering (held tickers first, news picked on this
machine). Runs on the owner's machine only; nothing here is sent to a model."""

from decimal import Decimal

from pathlib import Path

from investment_agent.market.watchlist import load_watchlist

from .news import pick_news
from .snapshot import BriefStore

NEWS_LIMIT = 8


def market_view(snapshot: dict | None, *, watched: list[str], held: set[str], news_limit: int = NEWS_LIMIT) -> dict | None:
    if not snapshot:
        return None
    board = snapshot.get("board") or {}
    symbols = board.get("symbols") or {}
    priced = board.get("status") == "ok"

    def row(s):
        r = symbols.get(s) or {}
        state = "no_price" if not priced or s not in symbols else "no_trade" if r.get("pct") is None else "ok"
        return {"symbol": s, **{k: r.get(k) for k in ("price", "change", "pct")}, "held": s in held, "sector": r.get("sector"), "state": state}
    first = [row(s) for s in sorted(held)]
    others = [row(s) for s in watched if s not in held]
    others.sort(key=lambda r: -abs(Decimal(r["pct"])) if r["pct"] is not None else 1)
    sector_names = {r["sector"] for r in first + others if r["sector"] and r["sector"] != "Khác"}
    news = snapshot.get("news") or {"status": "missing", "reason": "Chưa có tin"}
    if news.get("status") == "ok":
        news = {"status": "ok", "items": pick_news(news["items"], watched=watched, held=held, sector_names=sector_names, limit=news_limit)}
    view = {k: snapshot.get(k) for k in ("session_date", "updated_at", "indices", "hose", "proprietary")}
    view["board"] = {k: v for k, v in board.items() if k != "symbols"}
    return {**view, "tickers": first + others, "news": news}


def market_for_session(data_dir: Path | None, held: set[str]):
    """session date (ISO) -> market view, reading data/brief on demand; None when there is no data dir or snapshot."""
    if data_dir is None:
        return lambda session: None

    def view(session):
        # The market section is an extra: a corrupt watchlist or snapshot only drops it, never the brief or its delivery.
        try:
            watched = list(load_watchlist(Path(data_dir)).symbols)
            return market_view(BriefStore(Path(data_dir)).read(session), watched=watched, held=held) if session else None
        except Exception:
            return None
    return view
