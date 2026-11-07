from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.trend import SnapshotStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path, clock, repo=True):
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock,
                     personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()) if repo else None, data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def test_trend_returns_the_latest_snapshot_or_none(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, clock), clock, "GET", "/internal/trend").json() == {"snapshot": None}
    SnapshotStore(tmp_path / "trend").save({"session_date": "2026-10-23", "groups": []})
    assert call(client(tmp_path, clock), clock, "GET", "/internal/trend").json()["snapshot"]["session_date"] == "2026-10-23"


def test_trend_without_personal_store_is_unavailable(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, clock, repo=False), clock, "GET", "/internal/trend").status_code == 503


class FakeSource:
    def __init__(self):
        self.calls = []

    def board(self, symbols):
        self.calls.append(("board", tuple(symbols)))
        return [{"symbol": "FPT", "trading_date": "2026-10-30", "ref_price": 52700, "match_price": 53100}]

    def index_minutes(self, index):
        self.calls.append(("minutes", index))
        return []

    def get(self, url):
        self.calls.append(("get", url))
        raise RuntimeError("offline")

    def ohlcv(self, symbol, interval, start, end, index):
        self.calls.append(("ohlcv", symbol, interval, index))
        from datetime import datetime, timedelta, timezone
        return [{"time": datetime(2026, 10, 1, tzinfo=timezone(timedelta(hours=7))), "open": "1", "high": "2", "low": "1", "close": "2", "volume": 5}]


def test_board_and_chart_cover_the_watchlist_and_the_two_indices_only(tmp_path, monkeypatch):
    from investment_agent.api.routes import trend
    source = FakeSource()
    monkeypatch.setattr(trend, "_source", lambda: source)
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    clock = Clock()
    c = client(tmp_path, clock)
    board = call(c, clock, "GET", "/internal/trend/board").json()
    assert [r["symbol"] for r in board["rows"]] == ["DXY", "US10Y", "VN10Y", "GOLD", "USOIL", "BTC", "FPT"] and board["missing"] == ["VNINDEX", "VN30"]
    call(c, clock, "GET", "/internal/trend/board")
    assert [x for x in source.calls if x[0] == "board"] == [("board", ("FPT",))]  # cached between polls
    assert call(c, clock, "GET", "/internal/trend/chart/VNINDEX/1H").json()["bars"][0]["c"] == "2"
    assert ("ohlcv", "VNINDEX", "1H", True) in source.calls
    assert call(c, clock, "GET", "/internal/trend/chart/FPT/1D").json()["interval"] == "1D"
    weekly = call(c, clock, "GET", "/internal/trend/chart/FPT/1W").json()
    assert weekly["interval"] == "1W" and ("ohlcv", "FPT", "1W", False) not in source.calls  # built from the daily candles
    assert call(c, clock, "GET", "/internal/trend/chart/DXY/1M").json()["interval"] == "1M"
    assert call(c, clock, "GET", "/internal/trend/chart/FPT/1Y").status_code == 422
    assert call(c, clock, "GET", "/internal/trend/chart/DXY/1H").json()["reason"] == "Nguồn chỉ có giá ngày"
    assert call(c, clock, "GET", "/internal/trend/chart/ZZZ/1D").status_code == 404
    assert call(c, clock, "GET", "/internal/trend/chart/FPT/5m").status_code == 422


def test_outside_the_session_coins_stay_live_while_stocks_wait_five_minutes(tmp_path, monkeypatch):
    from investment_agent.api.routes import trend
    source = FakeSource()
    monkeypatch.setattr(trend, "_source", lambda: source)
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    clock = Clock(1_800_000_000 + 86_400)  # Saturday afternoon in Hà Nội
    c = client(tmp_path, clock)

    def counts():
        return sum(x[0] == "board" for x in source.calls), sum(x[0] == "get" for x in source.calls)
    call(c, clock, "GET", "/internal/trend/board")
    assert counts() == (1, 2)  # Bitcoin and gold
    clock.now += 20
    call(c, clock, "GET", "/internal/trend/board")
    assert counts() == (1, 4)
    clock.now += 300
    call(c, clock, "GET", "/internal/trend/board")
    assert counts() == (2, 6)


def test_price_alerts_are_listed_added_and_refused_for_unknown_tickers(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    clock = Clock()
    c = client(tmp_path, clock)
    empty = call(c, clock, "GET", "/internal/trend/alerts").json()
    assert empty == {"version": 0, "alerts": [], "telegram_ready": False}
    added = call(c, clock, "PUT", "/internal/trend/alerts", {"action": "add", "symbol": "VNINDEX", "op": "above", "price": "1800",
                                                             "expected_version": 0, "request_id": "p1"}).json()
    assert added["version"] == 1 and added["alerts"][0]["symbol"] == "VNINDEX"
    refused = call(c, clock, "PUT", "/internal/trend/alerts", {"action": "add", "symbol": "ZZZ", "op": "above", "price": "1",
                                                               "expected_version": 1, "request_id": "p2"})
    assert refused.status_code == 422 and refused.json()["code"] == "symbol_not_watched"
    stale = call(c, clock, "PUT", "/internal/trend/alerts", {"action": "remove", "id": added["alerts"][0]["id"], "expected_version": 0,
                                                             "request_id": "p3"})
    assert stale.status_code == 409


def test_chart_drawings_are_listed_added_and_refused_for_unknown_tickers(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    clock = Clock()
    c = client(tmp_path, clock)
    assert call(c, clock, "GET", "/internal/trend/drawings").json() == {"version": 0, "drawings": []}
    added = call(c, clock, "PUT", "/internal/trend/drawings", {"action": "add", "symbol": "FPT", "kind": "trend", "interval": "1D",
                                                               "points": [{"t": "2026-09-01", "p": "50"}, {"t": "2026-10-30", "p": "55.5"}],
                                                               "expected_version": 0, "request_id": "g1"}).json()
    assert added["version"] == 1 and added["drawings"][0]["points"][1] == {"t": "2026-10-30", "p": "55.5"}
    macro = call(c, clock, "PUT", "/internal/trend/drawings", {"action": "add", "symbol": "BTC", "kind": "hline", "price": "70000",
                                                               "expected_version": 1, "request_id": "g2"})
    assert macro.status_code == 200
    refused = call(c, clock, "PUT", "/internal/trend/drawings", {"action": "add", "symbol": "ZZZ", "kind": "hline", "price": "1",
                                                                 "expected_version": 2, "request_id": "g3"})
    assert refused.status_code == 422 and refused.json()["code"] == "symbol_not_watched"
    stale = call(c, clock, "PUT", "/internal/trend/drawings", {"action": "clear", "symbol": "FPT", "expected_version": 0, "request_id": "g4"})
    assert stale.status_code == 409


def test_chart_drawings_without_personal_store_are_unavailable(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, clock, repo=False), clock, "GET", "/internal/trend/drawings").status_code == 503


def test_channels_cover_the_trend_board_rows_on_weekly_daily_and_hourly_bars(tmp_path, monkeypatch):
    from investment_agent.api.routes import trend
    source = FakeSource()
    monkeypatch.setattr(trend, "_source", lambda: source)
    clock = Clock()
    c = client(tmp_path, clock)
    hpg = call(c, clock, "GET", "/internal/trend/channels/HPG/1W/5").json()
    assert hpg["symbol"] == "HPG" and hpg["basis"] == "ohlc" and hpg["frame"] == "W" and hpg["n"] == 5
    assert hpg["reason"] == "Chỉ có 1 nến tuần, cần ít nhất 35 nến để có MACD" and ("ohlcv", "HPG", "1D", False) in source.calls
    hourly = call(c, clock, "GET", "/internal/trend/channels/HPG/1H/4").json()
    assert hourly["frame"] == "H" and ("ohlcv", "HPG", "1H", False) in source.calls
    assert call(c, clock, "GET", "/internal/trend/channels/HPG/1D/12").json()["frame"] == "D"
    gold = call(c, clock, "GET", "/internal/trend/channels/GOLD/1W/5").json()
    assert gold["basis"] == "close" and gold["reason"] == "Chưa có số" and gold["note"] == "Gần đúng: PAXG, token bám giá vàng."
    assert call(c, clock, "GET", "/internal/trend/channels/DXY/1H/4").json()["reason"] == "Nguồn chỉ có giá ngày"
    assert call(c, clock, "GET", "/internal/trend/channels/ZZZ/1W/5").status_code == 404
    assert call(c, clock, "GET", "/internal/trend/channels/HPG/1W/0").status_code == 422
    assert call(c, clock, "GET", "/internal/trend/channels/HPG/1W/21").status_code == 422
    assert call(c, clock, "GET", "/internal/trend/channels/HPG/1D/61").status_code == 422
    assert call(c, clock, "GET", "/internal/trend/channels/HPG/1H/53").status_code == 422
    assert call(c, clock, "GET", "/internal/trend/channels/HPG/1M/5").status_code == 422


def test_weekly_channels_list_every_trend_board_row(tmp_path):
    clock = Clock()
    rows = call(client(tmp_path, clock), clock, "GET", "/internal/trend/channels").json()["rows"]
    assert rows[0] == {"id": "DXY", "label": "DXY"} and {"id": "GOLD", "label": "Vàng"} in rows and {"id": "VNINDEX", "label": "VN-Index"} in rows
