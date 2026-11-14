"""Bản đồ danh mục (every asset as a tile by layer) and Vì sao tài sản tháng này thay đổi (the securities account's month, cause by
cause), on Danh mục & Giao dịch. Owner-only views of the owner's own records; nothing here leaves the machine."""

import re
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.domain.asset_map import asset_map
from investment_agent.domain.month_bridge import month_bridge
from investment_agent.market.fund_nav import fund_profiles
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.deposit_book import book_quotes, read_book
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
def get_month_bridge(request: Request, month: str | None = None):
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
    return {"months": months, "bridge": month_bridge(events, closes=closes, sessions=sessions, month=month)}
