from datetime import datetime, timedelta, timezone

from investment_agent.market.live_board import ChartStore, build_board, chart, in_session

UTC = timezone.utc
VN = timezone(timedelta(hours=7))
NOW = datetime(2026, 10, 30, 3, 30, tzinfo=UTC)  # 10:30 in Hà Nội, a Friday


def test_session_hours_are_weekday_mornings_and_afternoons_in_vietnam_time():
    assert in_session(NOW) is True
    assert in_session(datetime(2026, 10, 30, 9, 0, tzinfo=UTC)) is False   # 16:00
    assert in_session(datetime(2026, 10, 31, 3, 30, tzinfo=UTC)) is False  # Saturday


def test_board_turns_dong_into_thousands_and_reads_indices_from_minute_bars():
    def board(symbols):
        assert symbols == ["ACB", "FPT", "VCB"]
        return [{"symbol": "FPT", "trading_date": "2026-10-30", "ref_price": 52700, "match_price": 53100, "ceiling": 56300, "floor": 49100,
                 "highest": 53300, "lowest": 52600, "accumulated_volume": 5661600},
                {"symbol": "ACB", "trading_date": "2026-10-30", "ref_price": 21300, "match_price": 0, "ceiling": 22700, "floor": 19900,
                 "highest": 0, "lowest": 0, "accumulated_volume": 0}]

    def minutes(index):
        return [(datetime(2026, 10, 29, 14, 45, tzinfo=VN), "1755.61"), (datetime(2026, 10, 30, 9, 15, tzinfo=VN), "1750.00"),
                (datetime(2026, 10, 30, 10, 29, tzinfo=VN), "1741.62")] if index == "VNINDEX" else []

    out = build_board(["ACB", "FPT", "VCB"], board=board, index_minutes=minutes, now=NOW)
    rows = {r["symbol"]: r for r in out["rows"]}
    assert rows["VNINDEX"] == {"symbol": "VNINDEX", "kind": "index", "price": "1741.62", "ref": "1755.61", "change": "-13.99",
                               "change_pct": "-0.0080", "ceiling": None, "floor": None, "high": None, "low": None, "volume": None,
                               "time": "2026-10-30T10:29:00+07:00"}
    assert rows["FPT"]["price"] == "53.1" and rows["FPT"]["ref"] == "52.7" and rows["FPT"]["change"] == "0.4" and rows["FPT"]["change_pct"] == "0.0076"
    assert rows["FPT"]["ceiling"] == "56.3" and rows["FPT"]["volume"] == 5661600
    assert rows["ACB"]["price"] is None and rows["ACB"]["change"] is None  # not traded yet: no price is made up from the reference
    assert "VCB" not in rows and "VN30" not in rows
    assert out["missing"] == ["VN30", "VCB"] and out["session_open"] is True and [r["symbol"] for r in out["rows"]] == ["VNINDEX", "ACB", "FPT"]


def test_a_failing_board_keeps_the_indices_and_says_so():
    def broken(symbols):
        raise RuntimeError("down")
    out = build_board(["FPT"], board=broken, index_minutes=lambda i: [], now=NOW)
    assert out["rows"] == [] and out["errors"] == ["Không đọc được bảng giá cổ phiếu (nguồn lỗi)"]


def _bars(n, start=datetime(2026, 1, 1, tzinfo=VN)):
    return [{"time": start + timedelta(days=i), "open": "10", "high": "20", "low": "9", "close": str(10 + i % 5), "volume": 100 + i} for i in range(n)]


def test_chart_bars_come_with_macd_and_rsi_and_are_cached_by_interval(tmp_path):
    calls = []

    def fetch(symbol, interval, start, end, index):
        calls.append((symbol, interval, index))
        return _bars(40) + [{"time": datetime(2026, 3, 1, tzinfo=VN), "open": "10", "high": "9", "low": "8", "close": "10", "volume": 1}]
    store = ChartStore(tmp_path)
    out = chart(store, "FPT", "1D", fetch=fetch, now=NOW, index=False)
    assert out["bars"][0] == {"t": "2026-01-01", "o": "10", "h": "20", "l": "9", "c": "10", "v": 100}
    assert out["macd"][-1]["t"] == "2026-02-09" and set(out["macd"][-1]) == {"t", "macd", "signal", "hist"} and len(out["macd"]) == 40 - 33
    assert out["rsi"][0]["t"] == "2026-01-15" and 0 <= out["rsi"][0]["v"] <= 100
    chart(store, "FPT", "1D", fetch=fetch, now=NOW + timedelta(minutes=5), index=False)
    assert calls == [("FPT", "1D", False)]
    hourly = chart(store, "FPT", "1H", fetch=lambda *a: _bars(3, datetime(2026, 10, 30, 9, tzinfo=VN)), now=NOW, index=False)
    assert hourly["bars"][0]["t"] == int(datetime(2026, 10, 30, 9, tzinfo=UTC).timestamp())  # Vietnam wall clock on the chart axis


def test_chart_keeps_the_saved_bars_when_the_source_fails(tmp_path):
    store = ChartStore(tmp_path)
    chart(store, "FPT", "1D", fetch=lambda *a: _bars(5), now=NOW, index=False)

    def broken(*a):
        raise RuntimeError("down")
    later = chart(store, "FPT", "1D", fetch=broken, now=NOW + timedelta(days=1), index=False)
    assert later["stale"] is True and len(later["bars"]) == 5
    assert chart(ChartStore(tmp_path / "e"), "FPT", "1D", fetch=broken, now=NOW, index=False)["reason"] == "Không đọc được dữ liệu nến (nguồn lỗi)"
