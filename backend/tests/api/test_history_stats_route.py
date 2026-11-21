from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path):
    start = date(2018, 1, 1)
    days = [start + timedelta(days=i) for i in range(700)]
    at = lambda d: datetime.combine(d, datetime.min.time())  # noqa: E731
    SeriesStore(tmp_path / "trend-sources").upsert("VNINDEX-1d", [(at(d), str(1000 + i)) for i, d in enumerate(days)])
    SeriesStore(tmp_path / "index-valuation").upsert("VNINDEX-pe-1d", [(at(d), str(10 + (i % 50) / 10)) for i, d in enumerate(days)])
    MacroStore(tmp_path).upsert("factor_oil", [(d, "50") for d in days], entry="auto")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock


def test_the_page_reads_one_horizon_at_a_time(tmp_path):
    c, clock = client(tmp_path)
    out = call(c, clock, "GET", "/internal/history-stats/60").json()
    assert out["h"] == 60 and out["horizons"] == [20, 60, 120, 250]
    assert len(out["pe"]["groups"]) == 5 and [lg["id"] for lg in out["lights"]] == ["oil", "usd", "us10y", "pe"]
    assert out["summary"].startswith("Hôm nay P/E VN-Index") and out["summary"].endswith("không phải dự báo hay khuyến nghị.")


def test_only_the_offered_horizons_are_accepted(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/history-stats/61").status_code == 422


def test_the_two_by_two_reads_two_conditions_and_the_usd_vnd_threshold(tmp_path):
    c, clock = client(tmp_path)
    out = call(c, clock, "GET", "/internal/history-stats/states/60/oil_up/pe_high/1").json()
    assert out["h"] == 60 and out["a"]["id"] == "oil_up" and out["b"]["id"] == "pe_high" and len(out["rows"]) == 4
    assert {c["id"] for c in out["conditions"]} >= {"cpi_up", "fx_up", "oil_up"} and "line" in out
    fx = next(c for c in out["conditions"] if c["id"] == "fx_up")
    assert fx["label"] == "Tỷ giá USD/VND tăng hơn 1% trong 3 tháng" and fx["state"] is None  # no World Bank figures in this test


def test_the_two_by_two_refuses_an_unknown_condition_or_threshold(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/history-stats/states/60/oil_up/nope/1").status_code == 422
    assert call(c, clock, "GET", "/internal/history-stats/states/60/oil_up/pe_high/7").status_code == 422
    assert call(c, clock, "GET", "/internal/history-stats/states/60/oil_up/oil_up/1").status_code == 422