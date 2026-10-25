import json
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from investment_agent.market.providers.vnstock_adapter import VnstockProvider
from investment_agent.market.trend_sources import coinbase_closes, fred_closes

VN = timezone(timedelta(hours=7))


class Frames:
    def __init__(self):
        self.calls = []

    def _frame(self, interval):
        if interval == "1H":
            times = [pd.Timestamp("2026-10-23 09:00").tz_localize("Asia/Ho_Chi_Minh"), pd.Timestamp("2026-10-23 10:00").tz_localize("Asia/Ho_Chi_Minh")]
        else:
            times = [pd.Timestamp("2026-10-22 07:00").tz_localize("Asia/Ho_Chi_Minh"), pd.Timestamp("2026-10-23 07:00").tz_localize("Asia/Ho_Chi_Minh")]
        return pd.DataFrame({"time": times, "open": [1, 1], "high": [2, 2], "low": [1, 1], "close": [57.0, float("nan")], "volume": [1, 1]})

    def equity(self, symbol):
        return self._sym(symbol, "equity")

    def index(self, symbol):
        return self._sym(symbol, "index")

    def _sym(self, symbol, kind):
        outer = self

        class S:
            def ohlcv(self, start=None, end=None, interval="1D", **kw):
                outer.calls.append((kind, symbol, interval, start, end))
                return outer._frame(interval)
        return S()


def test_vnstock_closes_for_stocks_and_indices_skip_missing_values():
    m = Frames()
    p = VnstockProvider(market=m, fundamental=object())
    hourly = p.fetch_closes("fpt", date(2026, 10, 1), date(2026, 10, 23), interval="1H", index=False)
    assert hourly == [(datetime(2026, 10, 23, 9, tzinfo=VN), "57")] and m.calls[0][:3] == ("equity", "FPT", "1H")
    p.fetch_closes("VN30", date(2026, 10, 1), date(2026, 10, 23), interval="1D", index=True)
    assert m.calls[1][:3] == ("index", "VN30", "1D")


def test_coinbase_pages_backwards_in_300_candle_windows_and_sorts():
    urls = []

    def get(url):
        urls.append(url)
        return json.dumps([[1792886400, 1, 2, 1, "4001.41", 1], [1792800000, 1, 2, 1, "3998.65", 1]])
    out = coinbase_closes(get, "PAXG-USD", 86400, date(2025, 1, 1), date(2026, 10, 24))
    assert len(urls) == 3 and all("granularity=86400" in u and "/products/PAXG-USD/candles" in u for u in urls)
    assert [t for t, _ in out] == sorted({t for t, _ in out})  # deduplicated across windows, oldest first
    assert out[-1] == (datetime(2026, 10, 25, tzinfo=timezone.utc), "4001.41")  # 1792886400 is 2026-10-25T00:00Z


def test_fred_closes_are_dated_daily_points():
    csv = "observation_date,DGS10\n2026-10-21,4.91\n2026-10-22,.\n2026-10-23,4.96\n"
    seen = []
    out = fred_closes(lambda url: seen.append(url) or csv, "DGS10", date(2018, 10, 25))
    assert out == [(datetime(2026, 10, 21), "4.91"), (datetime(2026, 10, 23), "4.96")] and "cosd=2018-10-25" in seen[0]
