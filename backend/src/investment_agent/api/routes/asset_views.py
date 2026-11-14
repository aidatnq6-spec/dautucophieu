"""Bản đồ danh mục (every asset as a tile by layer) and Vì sao tài sản tháng này thay đổi (the securities account's month, cause by
cause), on Danh mục & Giao dịch. Owner-only views of the owner's own records; nothing here leaves the machine."""

import re
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.domain.asset_map import asset_map
from investment_agent.domain.book_bridge import book_bridge
from investment_agent.domain.month_bridge import month_bridge
from investment_agent.market.fund_nav import fund_history, fund_profiles
from investment_agent.market.gold_price import gold_history
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.deposit_book import book_at, book_quotes, read_book
from investment_agent.services.overview import compose_overview
from investment_agent.services.records import LedgerBook, read_version

from ..auth import require_owner
from .common import error, now, unavailable

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@router.get("/asset-map")
def get_asset_map(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        overview = compose_overview(repo, owner, request.app.state.market, now(request))
        book, _ = read_book(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    data_dir = request.app.state.data_dir
    quotes = book_quotes(data_dir)
    sectors = load_sectors(Path(data_dir))[0] if data_dir is not None else {}
    return asset_map(overview["holdings"], ledger_cash=overview["ledger"]["cash"], book=book, navs=quotes["funds"], profiles=fund_profiles(data_dir),
                     gold=quotes["gold"], sectors=sectors, today=now(request).astimezone(VN).date())


def _months(first: date, today: date) -> list[str]:
    out, y, m = [], first.year, first.month
    while (y, m) <= (today.year, today.month):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out[::-1]


@router.get("/month-bridge")
@router.get("/month-bridge/{month}")
def get_month_bridge(request: Request, month: str | None = None):  # a path segment: the web proxy forwards no query string
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    if month is not None and not _MONTH.fullmatch(month):
        return error(422, "invalid_month", "Tháng theo dạng YYYY-MM.")
    try:
        events = list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)
    except RepositoryUnavailable:
        return unavailable()
    today = now(request).astimezone(VN).date()
    if not events:
        return {"months": [], "bridge": None}
    months = _months(min(e.effective_at for e in events), today)
    month = month or months[0]
    data_dir = request.app.state.data_dir
    closes, sessions = {}, []
    if data_dir is not None:
        store = SeriesStore(Path(data_dir) / "trend-sources")
        symbols = {e.security_id for e in events if getattr(e, "security_id", None)}
        closes = {s: {t.date(): v for t, v in store.read(f"{s}-1d")} for s in symbols}  # thousand đồng, adjusted
        sessions = [t.date() for t, _ in store.read("VNINDEX-1d") if t.date() <= today]
    bridge = month_bridge(events, closes=closes, sessions=sessions, month=month)
    book = None
    if bridge.get("end_day"):  # Sổ tài sản as last saved by the end of each day, valued at that day's NAV and gold price
        start_day = date.fromisoformat(bridge["start_day"]) if bridge.get("start_day") else None
        end_day = date.fromisoformat(bridge["end_day"])
        try:
            start_book = book_at(repo, owner, datetime.combine(start_day, time.max, VN)) if start_day else None
            end_book = book_at(repo, owner, datetime.combine(end_day, time.max, VN))
        except RepositoryUnavailable:
            return unavailable()
        if start_book is not None or end_book is not None:
            book = book_bridge(start_book, end_book, navs=fund_history(data_dir), gold=gold_history(data_dir), start_day=start_day, end_day=end_day)
    return {"months": months, "bridge": bridge, "book": book}


@router.get("/performance-daily")
def get_daily(request: Request):
    """Lịch nhiệt lãi/lỗ: each session of the last 26 weeks, the account's gain that day and the tickers that moved it."""
    from investment_agent.domain.month_bridge import daily_moves
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        events = list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)
    except RepositoryUnavailable:
        return unavailable()
    today = now(request).astimezone(VN).date()
    data_dir = request.app.state.data_dir
    closes, sessions = {}, []
    if data_dir is not None and events:
        store = SeriesStore(Path(data_dir) / "trend-sources")
        symbols = {e.security_id for e in events if getattr(e, "security_id", None)}
        closes = {s: {t.date(): v for t, v in store.read(f"{s}-1d")} for s in symbols}
        sessions = [t.date() for t, _ in store.read("VNINDEX-1d") if t.date() <= today]
    return {"days": daily_moves(events, closes=closes, sessions=sessions, today=today)}


@router.get("/held-charts")
def get_held_charts(request: Request):
    """Lưới biểu đồ nhỏ: each held ticker's last twelve months against VN-Index, both rebased to 100."""
    from investment_agent.domain.small_multiples import small_multiples
    from investment_agent.services.holdings_view import held_from_repo
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir = request.app.state.data_dir
    if repo is None:
        return unavailable()
    try:
        held = held_from_repo(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    if data_dir is None:
        return {"charts": [], "short": {}}
    store = SeriesStore(Path(data_dir) / "trend-sources")
    return small_multiples({s: store.read(f"{s}-1d") for s in sorted(held)}, index=store.read("VNINDEX-1d"), today=now(request).astimezone(VN).date())
