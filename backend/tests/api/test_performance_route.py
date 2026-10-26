from datetime import datetime

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_overview_route import MARKET, buy_fpt, setup_owner


def client(tmp_path, with_series=True):
    if with_series:
        series = SeriesStore(tmp_path / "trend-sources")
        series.upsert("FPT-1d", [(datetime(2027, 1, d), v) for d, v in ((5, "50"), (6, "55"), (7, "60"))])  # thousand đồng
        series.upsert("VNINDEX-1d", [(datetime(2027, 1, d), v) for d, v in ((5, "1000"), (6, "1010"), (7, "1030"))])
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=MARKET, data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    setup_owner(c, clock)
    buy_fpt(c, clock)  # deposit 100M on 04/01, buy 100 FPT at 50,000 on 05/01
    return c, clock


def test_performance_rebases_portfolio_and_vnindex_and_lists_gains_by_ticker(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/performance").json()
    assert [(p["date"], p["portfolio"], p["vnindex"]) for p in body["series"]] == [
        ("2027-01-05", "100.00", "100.00"), ("2027-01-06", "100.50", "101.00"), ("2027-01-07", "101.00", "103.00")]
    assert body["series"][-1]["value"] == "101000000"  # 95M cash + 100 × 60,000
    assert body["total"] == {"portfolio": "0.0100", "vnindex": "0.0300", "since": "2027-01-05", "days": 3}
    fpt = body["contributions"][0]
    assert fpt == {"symbol": "FPT", "cost": "5000000", "value": "6000000", "unrealized": "1000000"}
    assert body["realized_gain"] == "0" and body["ledger_started_on"] == "2027-01-04"


def test_without_index_history_there_is_no_series_but_gains_still_show(tmp_path):
    c, clock = client(tmp_path, with_series=False)
    body = call(c, clock, "GET", "/internal/performance").json()
    assert body["series"] == [] and body["total"] is None and body["contributions"][0]["unrealized"] == "1000000"
