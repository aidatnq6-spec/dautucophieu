"""Daily candles from VNDirect's public finfo API, in the shape the Vnstock adapter reads (market.equity(sym).ohlcv(...)).

Vnstock 6.0.0 (11/2026) dropped its free sources: every price source now needs the owner's own broker API key. VNDirect's
stock_prices carries the same adjusted prices the store already holds (adOpen…adClose, thousand đồng; checked against the stored
closes back to 2024, 13/11/2026) and vnmarket_prices the index levels; the statements already come from this API. Its robots.txt
answers 404, so nothing is disallowed. Daily candles only: hourly and minute candles raise DailyOnly. Volume is the matched
(order-book) volume, as before.
"""

import json
from typing import Callable

STOCK_URL = ("https://api-finfo.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{symbol}~date:gte:{start}~date:lte:{end}&size=9999"
             "&fields=code,date,adOpen,adHigh,adLow,adClose,nmVolume")
INDEX_URL = ("https://api-finfo.vndirect.com.vn/v4/vnmarket_prices?sort=date&q=code:{symbol}~date:gte:{start}~date:lte:{end}&size=9999"
             "&fields=code,date,open,high,low,close,nmVolume")
SOURCE_ID = "vndirect:finfo"


class DailyOnly(RuntimeError):
    code = "VNDIRECT_DAILY_ONLY"


def _default_get(url: str) -> str:
    import httpx
    response = httpx.get(url, timeout=30, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
    response.raise_for_status()
    return response.text


class _Handle:
    def __init__(self, get: Callable[[str], str], symbol: str, index: bool):
        self._get, self._symbol, self._index = get, symbol.upper(), index

    def ohlcv(self, start: str, end: str, interval: str = "1D", **_ignored):
        import pandas as pd
        if interval != "1D":
            raise DailyOnly(f"VNDirect serves daily candles only, not {interval}")
        url = (INDEX_URL if self._index else STOCK_URL).format(symbol=self._symbol, start=start[:10], end=end[:10])
        rows = json.loads(self._get(url)).get("data", [])
        keys = ("open", "high", "low", "close") if self._index else ("adOpen", "adHigh", "adLow", "adClose")
        out = []
        for r in rows:
            if r.get("code", self._symbol).upper() != self._symbol or any(r.get(k) is None for k in keys):
                continue
            out.append({"time": pd.Timestamp(r["date"]), **{name: r[k] for name, k in zip(("open", "high", "low", "close"), keys)},
                        "volume": int(r.get("nmVolume") or 0)})
        frame = pd.DataFrame(out, columns=["time", "open", "high", "low", "close", "volume"])
        return frame.sort_values("time").reset_index(drop=True)


class VndirectMarket:
    source_id = SOURCE_ID

    def __init__(self, get: Callable[[str], str] | None = None):
        self._get = get or _default_get

    def equity(self, symbol: str) -> _Handle:
        return _Handle(self._get, symbol, index=False)

    def index(self, symbol: str) -> _Handle:
        return _Handle(self._get, symbol, index=True)
