import json
from datetime import date, datetime, timedelta, timezone

from investment_agent.market.leading import MacroStore
from investment_agent.market.macro_board import macro_chart, macro_rows
from investment_agent.market.series import SeriesStore

NOW = datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc)


def _seed(tmp_path):
    days = SeriesStore(tmp_path / "trend-sources")
    days.upsert("DXY-ecb-1d", [(datetime(2026, 10, 29), "99.37"), (datetime(2026, 10, 30), "99.48")])
    days.upsert("DXY-1d", [(datetime(2026, 10, 16), "121.4048")])  # FRED's broad dollar index the row used before: a different measure
    days.upsert("US10Y-1d", [(datetime(2026, 10, 28), "4.10"), (datetime(2026, 10, 29), "4.07")])
    days.upsert("BTC-1d", [(datetime(2026, 10, 29), "77000"), (datetime(2026, 10, 30), "77873.27")])
    days.upsert("GOLD-1d", [(datetime(2026, 10, 30), "3996.96")])
    MacroStore(tmp_path).upsert("vn10y", [(date(2026, 10, 29), "4.47"), (date(2026, 10, 30), "4.49")], entry="auto")


def test_daily_rows_compare_the_last_two_closes_and_coins_are_live_against_24_hours_before(tmp_path):
    _seed(tmp_path)
    urls = []

    def get(url):
        urls.append(url)
        return json.dumps({"open": "77873.27", "last": "77147.67"}) if "BTC-USD" in url else json.dumps({"open": "3996.96", "last": "3891.58"})
    rows = {r["symbol"]: r for r in macro_rows(tmp_path, get=get, now=NOW)}
    assert list(rows) == ["DXY", "US10Y", "VN10Y", "GOLD", "USOIL", "BTC"]
    assert rows["DXY"] == {"symbol": "DXY", "kind": "macro", "label": "DXY", "price": "99.48", "ref": "99.37", "change": "0.11",
                           "change_pct": "0.0011", "time": "2026-10-30", "basis": "close", "unit": "điểm", "reason": None}
    assert rows["US10Y"]["price"] == "4.07" and rows["US10Y"]["change"] == "-0.03" and rows["US10Y"]["unit"] == "%"
    assert rows["VN10Y"]["price"] == "4.49" and rows["VN10Y"]["change"] == "0.02" and rows["VN10Y"]["time"] == "2026-10-30"
    assert rows["BTC"]["price"] == "77147.67" and rows["BTC"]["ref"] == "77873.27" and rows["BTC"]["basis"] == "24h" and rows["BTC"]["time"] == NOW.isoformat()
    assert rows["GOLD"]["label"] == "Vàng" and rows["GOLD"]["price"] == "3891.58"
    assert rows["USOIL"]["price"] is None and rows["USOIL"]["reason"] == "Chưa có số"
    assert len(urls) == 2 and all("api.exchange.coinbase.com/products/" in u and u.endswith("/stats") for u in urls)


def test_a_failing_coin_feed_falls_back_to_the_last_daily_close(tmp_path):
    _seed(tmp_path)

    def broken(url):
        raise RuntimeError("down")
    rows = {r["symbol"]: r for r in macro_rows(tmp_path, get=broken, now=NOW)}
    assert rows["BTC"]["price"] == "77873.27" and rows["BTC"]["basis"] == "close" and rows["BTC"]["time"] == "2026-10-30"
    assert rows["GOLD"]["price"] == "3996.96" and rows["GOLD"]["change"] is None  # one close only: no change is made up


def test_macro_chart_is_a_close_line_with_indicators_and_hourly_only_where_the_source_has_it(tmp_path):
    days = SeriesStore(tmp_path / "trend-sources")
    days.upsert("DXY-ecb-1d", [(datetime(2026, 1, 1) + timedelta(days=i), str(100 + i % 3)) for i in range(40)])
    SeriesStore(tmp_path / "intraday").upsert("BTC-1h", [(datetime(2026, 10, 30, 9, tzinfo=timezone.utc), "77000")])
    out = macro_chart(tmp_path, "DXY", "1D")
    assert out["style"] == "line" and out["bars"][0] == {"t": "2026-01-01", "c": "100"} and len(out["macd"]) == 7 and out["rsi"]
    assert out["fetched_at"] is None and out["as_of"] == "2026-02-09" and out["unit"] == "điểm"
    assert macro_chart(tmp_path, "DXY", "1H")["reason"] == "Nguồn chỉ có giá ngày"
    hourly = macro_chart(tmp_path, "BTC", "1H")
    assert hourly["bars"] == [{"t": int(datetime(2026, 10, 30, 16, tzinfo=timezone.utc).timestamp()), "c": "77000"}]  # Hà Nội wall clock
    assert macro_chart(tmp_path, "USOIL", "1D")["reason"] == "Chưa có số"
