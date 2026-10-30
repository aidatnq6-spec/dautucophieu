"""Hồ sơ doanh nghiệp: one ticker's quick facts, reference valuation, events and sector insights in one read.

Everything shown is already stored by the other pages (public prices, statements, events, report claims); only the
held flag comes from the owner's ledger, and nothing here reaches the AI.
"""

import re
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.insights.store import InsightStore
from investment_agent.insights.summary import link, linking_sectors, summarise
from investment_agent.market.corporate_events import EventStore
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.prices import PriceStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.holdings_view import fair_value_board
from investment_agent.valuation.reference import metrics

from ..auth import require_owner
from .common import error, now, unavailable
from .insights import WINDOW_DAYS
from .watchlist import held_tickers

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
VOLUME_SESSIONS, PAST_DAYS, INSIDER_DAYS = 20, 365, 90


def _facts(data_dir: Path, market, symbol: str, today) -> dict:
    """Verified price × shares for market value; adjusted daily closes (thousand đồng) for the change and the 52-week range."""
    point = market.price(symbol)
    closes = SeriesStore(data_dir / "trend-sources").read(f"{symbol}-1d")
    year = [Decimal(str(v)) * 1000 for t, v in closes if t.date() > today - timedelta(days=364)]
    change = None
    if len(closes) >= 2 and closes[-2][1] > 0:
        change = str(((Decimal(str(closes[-1][1])) / Decimal(str(closes[-2][1]))) - 1).quantize(Decimal("0.0001"), ROUND_HALF_UP))
    record = FundamentalsStore(data_dir / "fundamentals").read(symbol)
    m = metrics(record, today=today, year_end_prices={}) if record and record.get("years") else None
    shares = int(m["shares"]) if m else None
    bars = [bar for bar, _ in sorted(PriceStore(data_dir).latest(symbol).values(), key=lambda br: br[0].session_date)][-VOLUME_SESSIONS:]
    return {"price": format(point.price, "f") if point else None, "price_date": point.session_date.isoformat() if point else None,
            "change_pct": change, "high_52w": format(max(year).normalize(), "f") if year else None,
            "low_52w": format(min(year).normalize(), "f") if year else None, "shares": shares,
            "market_cap": format((point.price * shares).quantize(Decimal(1)), "f") if point and shares else None,
            "avg_volume": round(sum(b.volume for b in bars) / len(bars)) if bars else None, "avg_volume_sessions": len(bars)}


def _events(data_dir: Path, symbol: str, today) -> dict:
    rows = EventStore(data_dir).events([symbol])
    day, past, insider = today.isoformat(), (today - timedelta(days=PAST_DAYS)).isoformat(), (today - timedelta(days=INSIDER_DAYS)).isoformat()
    main = [e for e in rows if e["kind"] != "insider"]
    return {"upcoming": sorted((e for e in main if e["key_date"] and e["key_date"] >= day), key=lambda e: e["key_date"]),
            "past": sorted((e for e in main if e["key_date"] and past <= e["key_date"] < day), key=lambda e: e["key_date"], reverse=True),
            "undated": [e for e in main if not e["key_date"]],
            "insider": sorted((e for e in rows if e["kind"] == "insider" and e["key_date"] and e["key_date"] >= insider),
                              key=lambda e: e["key_date"], reverse=True)}


@router.get("/stock/{symbol}")
def stock(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir = request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    symbol = symbol.upper()
    if not _SYMBOL.fullmatch(symbol):
        return error(400, "invalid_symbol", "Mã cổ phiếu không hợp lệ.")
    data_dir, today = Path(data_dir), now(request).astimezone(VN).date()
    watched = set(load_watchlist(data_dir).symbols)
    sectors = load_sectors(data_dir)[0]
    try:
        held = held_tickers(request)
        rows = fair_value_board(data_dir, request.app.state.market, repo, owner, held=held, today=today)["rows"]
    except RepositoryUnavailable:
        return unavailable()
    for row in rows:
        for m in row["methods"]:
            m["value"] = str(m["value"]) if m["value"] is not None else None
    summary = link(summarise(InsightStore(data_dir / "insights").recent(today, days=WINDOW_DAYS)),
                   sectors=linking_sectors(sectors, watched=watched, held=held), valuation_rows=rows, held=held)
    sector = sectors.get(symbol)
    return {"symbol": symbol, "sector": sector, "watched": symbol in watched, "held": symbol in held,
            "facts": _facts(data_dir, request.app.state.market, symbol, today),
            "valuation": next((r for r in rows if r["symbol"] == symbol), None) if symbol in watched else None,
            "events": _events(data_dir, symbol, today),
            "insights": {"sector": next((s for s in summary["sectors"] if sector and s["sector"] == sector), None), "window_days": WINDOW_DAYS}}
