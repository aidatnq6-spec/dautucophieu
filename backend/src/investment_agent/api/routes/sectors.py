"""Toàn ngành: the sectors of the watched tickers, and for one of them the heatmap of quarterly results and the sector's P/B over
time. Public statements and prices only; nothing personal is read."""

import re
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.domain.sector_view import heatmap, sector_key, valuation
from investment_agent.market.financial_ratios import kind_of
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.valuation.history import monthly_multiples
from investment_agent.valuation.sources import valuation_record

from ..auth import require_owner
from .common import error, now, unavailable

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
_KEY = re.compile(r"^[a-z0-9-]{1,80}$")


def _members(data_dir: Path) -> dict[str, list[str]]:
    sectors = load_sectors(data_dir)[0]
    out: dict[str, list[str]] = {}
    for symbol in load_watchlist(data_dir).symbols:
        if sectors.get(symbol):
            out.setdefault(sectors[symbol], []).append(symbol)
    return {name: sorted(symbols) for name, symbols in out.items()}


@router.get("/sectors")
def list_sectors(request: Request):
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    members = _members(Path(data_dir))
    return {"sectors": [{"key": sector_key(name), "name": name, "count": len(symbols)} for name, symbols in sorted(members.items())]}


@router.get("/sectors/{key}")
def one_sector(key: str, request: Request):
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    data_dir = Path(data_dir)
    match = next(((name, symbols) for name, symbols in _members(data_dir).items() if _KEY.fullmatch(key) and sector_key(name) == key), None)
    if match is None:
        return error(404, "sector_not_found", "Không có ngành này trong danh sách theo dõi.")
    name, symbols = match
    store = StatementStore(data_dir / ("statements" if kind_of(name) is None else "statements-financial"))
    records = {s: (store.read(s) or {}).get("quarters", {}) for s in symbols}
    today = now(request).astimezone(VN).date()
    series = {}
    for s in symbols:
        v = valuation_record(data_dir, s, today=today)
        hist = monthly_multiples(v["record"], SeriesStore(data_dir / "trend-sources").read(f"{s}-1d"), today=today, shares=v["shares"],
                                 published=v["published"])
        series[s] = [(p["month"], None if p["value"] is None else str(p["value"])) for p in hist["pb"]["points"]]
    return {"key": key, "name": name, "members": symbols, "financial": kind_of(name) is not None,
            "heatmap": heatmap({s: r for s, r in records.items() if r}), "valuation": valuation(series)}
