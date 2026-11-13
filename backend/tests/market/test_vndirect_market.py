import json
from datetime import date, datetime, timezone

import pytest

from investment_agent.market.providers.vndirect_market import DailyOnly, VndirectMarket
from investment_agent.market.providers.vnstock_adapter import VnstockProvider

NOW = datetime(2026, 11, 13, 9, tzinfo=timezone.utc)


def stock_rows():
    return {"data": [  # newest first, as VNDirect sends them
        {"code": "FPT", "date": "2026-11-13", "adOpen": 49.6, "adHigh": 50.3, "adLow": 49.4, "adClose": 50.1, "nmVolume": 14372200.0, "close": 50.1},
        {"code": "FPT", "date": "2026-11-12", "adOpen": 50.9, "adHigh": 51.0, "adLow": 49.5, "adClose": 49.55, "nmVolume": 17335200.0, "close": 49.55},
        {"code": "FPT", "date": "2026-11-11", "adOpen": 50.9, "adHigh": 50.9, "adLow": 50.9, "adClose": 50.9, "nmVolume": 0.0, "close": 50.9}]}


def index_rows():
    return {"data": [{"code": "VNINDEX", "date": "2026-11-13", "open": 1727.31, "high": 1737.36, "low": 1698.21, "close": 1734.93, "nmVolume": 453533975.0}]}


class Get:
    def __init__(self):
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        return json.dumps(index_rows() if "vnmarket_prices" in url else stock_rows())


def test_stock_candles_are_the_adjusted_prices_oldest_first():
    get = Get()
    frame = VndirectMarket(get=get).equity("fpt").ohlcv(start="2026-11-11", end="2026-11-13", interval="1D", source="kbs", floating=None)
    assert list(frame.columns) == ["time", "open", "high", "low", "close", "volume"]
    assert [t.date().isoformat() for t in frame["time"]] == ["2026-11-11", "2026-11-12", "2026-11-13"]
    assert frame.iloc[-1]["close"] == 50.1 and frame.iloc[-1]["volume"] == 14372200
    assert "stock_prices" in get.urls[0] and "code:FPT~" in get.urls[0] and "date:gte:2026-11-11~date:lte:2026-11-13" in get.urls[0]


def test_index_candles_come_from_the_market_prices():
    get = Get()
    frame = VndirectMarket(get=get).index("VNINDEX").ohlcv(start="2026-11-13", end="2026-11-13", interval="1D")
    assert frame.iloc[0]["close"] == 1734.93 and "vnmarket_prices" in get.urls[0]


def test_only_daily_candles_are_served():
    with pytest.raises(DailyOnly) as err:
        VndirectMarket(get=Get()).equity("FPT").ohlcv(start="2026-11-13", end="2026-11-13", interval="1H")
    assert err.value.code == "VNDIRECT_DAILY_ONLY"


def test_the_provider_reads_prices_from_vndirect_by_default_and_skips_no_trade_days():
    p = VnstockProvider(market=VndirectMarket(get=Get()), fundamental=object(), clock=lambda: NOW)
    bars = p.fetch_prices("FPT", date(2026, 11, 11), date(2026, 11, 13))
    assert [b.session_date.isoformat() for b in bars] == ["2026-11-12", "2026-11-13"]  # 11/11 had no matched volume
    assert bars[-1].close == 50100 and bars[-1].price_basis == "adjusted" and bars[-1].source_id == "vndirect:finfo"
    index = p.fetch_index("VNINDEX", date(2026, 11, 13), date(2026, 11, 13))
    assert str(index[0].close) == "1734.93" and index[0].source_id == "vndirect:finfo"
