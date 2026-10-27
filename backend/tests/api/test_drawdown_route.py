from datetime import datetime

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_overview_route import MARKET, buy_fpt, setup_owner  # FPT bought 100 × 50,000; MARKET prices FPT at 60,000


def client(tmp_path):
    series = SeriesStore(tmp_path / "trend-sources")
    series.upsert("FPT-1d", [(datetime(2008, 1, d), v) for d, v in ((2, "40"), (3, "20"), (4, "45"), (7, "60"))])  # thousand đồng
    series.upsert("VNINDEX-1d", [(datetime(2008, 1, d), v) for d, v in ((2, "1000"), (3, "400"), (4, "500"), (7, "900"))])
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=MARKET, data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    setup_owner(c, clock)
    buy_fpt(c, clock)
    return c, clock


def test_vnindex_and_each_held_ticker_show_their_deepest_fall_now_and_against_cost(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/drawdown").json()
    assert body["threshold"] == "0.30"
    index, fpt = body["rows"]
    assert index["symbol"] == "VNINDEX" and index["max"] == {"depth": "-0.6000", "peak": "2008-01-02", "trough": "2008-01-03", "recovered": None}
    assert index["current"] == {"depth": "-0.1000", "peak": "2008-01-02"} and index["since"] == "2008-01-02" and index["vs_cost"] is None
    assert fpt["symbol"] == "FPT" and fpt["max"]["depth"] == "-0.5000" and fpt["max"]["recovered"] == "2008-01-04"
    assert fpt["vs_cost"] == "0.2000" and fpt["hit"] is False


def test_the_threshold_is_set_in_settings_and_flags_tickers_below_it(tmp_path):
    c, clock = client(tmp_path)
    ok = call(c, clock, "PUT", "/internal/settings/portfolio", {"settings": {"concentration_limit": "0.25", "journal_review_threshold": "0.15",
                                                                             "drawdown_threshold": "0.1"}, "expected_version": 0, "request_id": "pf1"})
    assert ok.status_code == 200
    assert call(c, clock, "GET", "/internal/drawdown").json()["threshold"] == "0.1"
    bad = call(c, clock, "PUT", "/internal/settings/portfolio", {"settings": {"drawdown_threshold": "1.5"}, "expected_version": 1, "request_id": "pf2"})
    assert bad.status_code == 422
