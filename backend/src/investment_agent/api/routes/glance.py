"""Tổng quan at a glance: quick numbers for the last session and one list of things worth a look today.

Everything here is gathered from views that already exist (holdings, Xu hướng closes, performance, Lịch sự kiện, Phân bổ, Nhật ký,
Bản tin); nothing new is decided and nothing is sent anywhere.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.domain.journal import due_reviews
from investment_agent.domain.ledger import replay
from investment_agent.domain.time_weighted import performance
from investment_agent.jobs.publication import list_reports
from investment_agent.market.corporate_events import REMINDED_KINDS, EventStore
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.equity_budget import budget_view
from investment_agent.services.journal import read_journal
from investment_agent.services.overview import compose_overview
from investment_agent.services.records import LedgerBook, portfolio_settings, read_version

from ..auth import require_owner
from .common import now, unavailable
from .concentration import concentration_view
from .events import REMIND_DAYS

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
_Q4 = Decimal("0.0001")


def _ratio(a: Decimal, b: Decimal) -> str | None:
    return str((a / b).quantize(_Q4, ROUND_HALF_UP)) if b else None


@router.get("/glance")
def glance(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    market, data_dir = request.app.state.market, request.app.state.data_dir
    today = now(request).astimezone(VN).date()
    try:
        view = compose_overview(repo, owner, market, now(request))
        events = list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)
        budget, _ = budget_view(repo, owner)
        entries, _ = read_journal(repo, owner)
        threshold = portfolio_settings(repo, owner)[0].journal_review_threshold
        reports = list_reports(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    held = [h for h in view["holdings"] if h["quantity"] + h["pending_quantity"] > 0]
    series = SeriesStore(Path(data_dir) / "trend-sources") if data_dir is not None else None

    # Quick numbers: value and unrealised gain at today's prices; the last session's move from stored daily closes (thousand đồng).
    value = sum((Decimal(h["market_value"]) for h in held if h["market_value"] is not None), Decimal(0))
    gain = sum((Decimal(h["unrealized_gain"]) for h in held if h["unrealized_gain"] is not None), Decimal(0))
    day_change, day_base, session = Decimal(0), Decimal(0), None
    index_points = series.read("VNINDEX-1d") if series else []
    if len(index_points) >= 2:
        session = index_points[-1][0].date()
    for h in held:
        closes = series.read(f"{h['security_id']}-1d") if series else []
        if len(closes) >= 2:
            shares = h["quantity"] + h["pending_quantity"]
            last, prev = Decimal(str(closes[-1][1])) * 1000, Decimal(str(closes[-2][1])) * 1000
            day_change += shares * (last - prev)
            day_base += shares * prev
    closes_by_symbol = {}
    if series:
        closes_by_symbol = {s: {t.date(): v * 1000 for t, v in series.read(f"{s}-1d")}
                            for s in {e.security_id for e in events if getattr(e, "security_id", None)}}
    perf = performance(events, closes=closes_by_symbol, index={t.date(): v for t, v in index_points}, today=today)["total"] if events else None
    kpis = {"market_value": str(value), "unrealized_gain": str(gain),
            "day_change": str(day_change.quantize(Decimal(1), ROUND_HALF_UP)) if day_base else None, "day_change_ratio": _ratio(day_change, day_base),
            "vnindex": str(Decimal(str(index_points[-1][1])).normalize()) if index_points else None,
            "vnindex_change_ratio": _ratio(Decimal(str(index_points[-1][1])) - Decimal(str(index_points[-2][1])), Decimal(str(index_points[-2][1])))
            if len(index_points) >= 2 else None,
            "performance": perf, "room": budget.get("room") if budget["status"] == "ok" else None,
            "over_budget": budget.get("over") if budget["status"] == "ok" else None}

    # Worth a look: held tickers' corporate events within the reminder window, concentration flags, journal entries due for review.
    held_symbols = {h["security_id"] for h in held}
    upcoming = []
    if data_dir is not None:
        ahead = (today + timedelta(days=REMIND_DAYS)).isoformat()
        upcoming = sorted(({"symbol": e["symbol"], "kind": e["kind"], "title": e["title"], "key_date": e["key_date"]}
                           for e in EventStore(Path(data_dir)).events(sorted(held_symbols))
                           if e["kind"] in REMINDED_KINDS and e["key_date"] and today.isoformat() <= e["key_date"] <= ahead),
                          key=lambda e: (e["key_date"], e["symbol"]))
    conc = concentration_view(request)
    over = []
    if isinstance(conc, dict) and conc.get("status") == "ok":
        over = [{"name": t["symbol"], "kind": "ticker", "weight": t["weight"]} for t in conc["tickers"] if t["over"]]
        over += [{"name": s["sector"], "kind": "sector", "weight": s["weight"]} for s in conc["sectors"] if s["over"] and len(s["symbols"]) > 1]
    prices = {h["security_id"]: Decimal(h["price"]) for h in held if h["price"] is not None}
    for e in entries:
        if e.symbol not in prices and (point := market.price(e.symbol)) is not None:
            prices[e.symbol] = point.price
    reviews = [{"entry_id": d["entry"].entry_id, "symbol": d["entry"].symbol, "kind": d["entry"].kind, "change": d["change"]}
               for d in due_reviews(entries, prices=prices, threshold=threshold)]
    latest = reports[-1] if reports else None
    return {"session_date": session.isoformat() if session else None, "kpis": kpis,
            "attention": {"events": upcoming, "over_limit": over, "journal_reviews": reviews,
                          "latest_report": {"report_id": latest["report_id"], "session_date": latest["session_date"]} if latest else None}}

