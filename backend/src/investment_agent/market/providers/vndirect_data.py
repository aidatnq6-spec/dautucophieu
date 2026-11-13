"""The HOSE listing, the end-of-day board and corporate events from VNDirect's public finfo API, after Vnstock 6.0.0 (11/2026)
dropped the free sources the brief and Lịch sự kiện used (VCI listing, price board and company events). No key; robots.txt answers
404, so nothing is disallowed (checked 13/11/2026).

The board rows keep the shape and units Vnstock's price board had, so the brief's maths is unchanged: prices in đồng, matched value
in million đồng, foreign values in đồng. The board is end of day (VNDirect's daily prices), not live. A ticker without a trade has
match_price 0, as before; one without a foreign row has no foreign figures (not zero).
"""

import json
from datetime import date, timedelta
from typing import Callable

BASE = "https://api-finfo.vndirect.com.vn/v4/"
LISTING_URL = BASE + "stocks?q=type:STOCK~floor:HOSE~status:LISTED&size=9999&fields=code,type,floor"
INDUSTRY_URL = BASE + "industry_classification?q=industryLevel:2&size=100"
BOARD_URL = (BASE + "stock_prices?q=floor:HOSE~date:gte:{start}~date:lte:{end}&size=9999"
             "&fields=code,date,basicPrice,close,nmVolume,nmValue,ceilingPrice,floorPrice,high,low")
INDEX_LEVELS_URL = BASE + "vnmarket_prices?sort=date:desc&q=code:{index}~date:gte:{start}&size=10&fields=code,date,close"
FOREIGN_URL = BASE + "foreigns?q=floor:HOSE~tradingDate:{day}&size=9999"
EVENTS_URL = BASE + "events?q=code:{symbol}~disclosureDate:gte:{since}&size=500&sort=disclosureDate:desc"
BOARD_LOOKBACK_DAYS = 10


def default_get(url: str) -> str:
    import httpx
    response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
    response.raise_for_status()
    return response.text


def _data(get: Callable[[str], str], url: str) -> list[dict]:
    return json.loads(get(url)).get("data", [])


def hose_listing(get: Callable[[str], str] = default_get, *, known_names: dict[str, str] | None = None) -> dict:
    """HOSE stock symbols, each one's ICB level-2 code and the level-2 names. Names already known (the ones the brief has shown so
    far) are kept, so a sector keeps its name; VNDirect's name is used for a code not seen before."""
    symbols = sorted({str(r["code"]).upper() for r in _data(get, LISTING_URL) if r.get("code")})
    wanted, codes, names = set(symbols), {}, {}
    for row in _data(get, INDUSTRY_URL):
        code = str(row.get("industryCode") or "")
        if not code:
            continue
        names[code] = str(row.get("vietnameseName") or code).strip()
        for symbol in str(row.get("codeList") or "").split(","):
            if symbol.strip().upper() in wanted:
                codes[symbol.strip().upper()] = code
    return {"symbols": symbols, "icb_codes": codes, "icb_names": {**names, **{c: n for c, n in (known_names or {}).items() if c in names}}}


def price_board(symbols: list[str], get: Callable[[str], str] = default_get, *, today: date | None = None) -> list[dict]:
    """The latest session's end-of-day row of each asked symbol, in the units Vnstock's price board used."""
    today = today or date.today()
    rows = _data(get, BOARD_URL.format(start=(today - timedelta(days=BOARD_LOOKBACK_DAYS)).isoformat(), end=today.isoformat()))
    if not rows:
        return []
    latest = max(r["date"] for r in rows)
    foreign = {str(f["code"]).upper(): f for f in _data(get, FOREIGN_URL.format(day=latest))}
    wanted, out = {s.upper() for s in symbols}, []
    for r in rows:
        symbol = str(r.get("code") or "").upper()
        if r.get("date") != latest or symbol not in wanted:
            continue
        traded = (r.get("nmVolume") or 0) > 0
        f = foreign.get(symbol)
        thousand = lambda field: round(r[field] * 1000) if r.get(field) else None  # noqa: E731 - thousand đồng to đồng
        out.append({"symbol": symbol, "trading_date": latest, "ref_price": round((r.get("basicPrice") or 0) * 1000),
                    "ceiling": thousand("ceilingPrice"), "floor": thousand("floorPrice"),
                    "highest": thousand("high") if traded else None, "lowest": thousand("low") if traded else None,
                    "match_price": round((r.get("close") or 0) * 1000) if traded else 0,
                    "accumulated_value": (r.get("nmValue") or 0) / 1_000_000, "accumulated_volume": int(r.get("nmVolume") or 0),
                    "foreign_buy_volume": int(f["buyVol"]) if f and f.get("buyVol") is not None else None,
                    "foreign_sell_volume": int(f["sellVol"]) if f and f.get("sellVol") is not None else None,
                    "foreign_buy_value": f.get("buyVal") if f else None, "foreign_sell_value": f.get("sellVal") if f else None})
    return out


def sector_codes(get: Callable[[str], str] = default_get) -> dict[str, tuple[str, str]]:
    """Every listed ticker VNDirect classifies at ICB level 2: symbol → (code, VNDirect's own name)."""
    out = {}
    for row in _data(get, INDUSTRY_URL):
        code = str(row.get("industryCode") or "")
        for symbol in str(row.get("codeList") or "").split(","):
            if code and symbol.strip():
                out[symbol.strip().upper()] = (code, str(row.get("vietnameseName") or code).strip())
    return out


def index_members(group: str, get: Callable[[str], str] = default_get) -> list[str]:
    """Members of an index group as VNDirect's listing marks them; only VN30 is marked, so other groups come back empty."""
    rows = _data(get, BASE + f"stocks?q=indexCode:{group}&size=500&fields=code,indexCode")
    return sorted({str(r["code"]).upper() for r in rows if str(r.get("indexCode") or "") == group and r.get("code")})


def index_levels(index: str, get: Callable[[str], str] = default_get, *, today: date | None = None) -> list[tuple]:
    """The last two closes of an index as (15:00 of that day, level), oldest first: the board shows the last against the one
    before (end of day; VNDirect serves no minute bars)."""
    from datetime import datetime, time, timezone
    vn = timezone(timedelta(hours=7))
    start = ((today or date.today()) - timedelta(days=14)).isoformat()
    rows = sorted(_data(get, INDEX_LEVELS_URL.format(index=index.upper(), start=start)), key=lambda r: r["date"])[-2:]
    return [(datetime.combine(date.fromisoformat(r["date"]), time(15, 0), vn), format(r["close"], "f") if isinstance(r["close"], str)
             else str(r["close"])) for r in rows if r.get("close")]


def events(symbol: str, get: Callable[[str], str] = default_get, *, today: date | None = None, years: int = 2) -> list[dict]:
    """The ticker's events disclosed in the last `years` years (raw VNDirect rows; corporate_events.normalise reads them)."""
    since = ((today or date.today()) - timedelta(days=365 * years)).isoformat()
    return _data(get, EVENTS_URL.format(symbol=symbol.upper(), since=since))
