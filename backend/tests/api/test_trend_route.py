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
    assert call(c, clock, "GET", "/internal/trend/chart/DXY/1H").json()["reason"] == "Nguồn chỉ có giá ngày"
    assert call(c, clock, "GET", "/internal/trend/chart/ZZZ/1D").status_code == 404
    assert call(c, clock, "GET", "/internal/trend/chart/FPT/5m").status_code == 422
