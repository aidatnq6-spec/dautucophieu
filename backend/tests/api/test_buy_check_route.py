from datetime import datetime

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_overview_route import MARKET, buy_fpt, setup_owner  # FPT bought 100 × 50,000 = 5 tr; 1 tỷ investable capital


def client(tmp_path):
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(2026, 10, 1), "40"), (datetime(2027, 1, 14), "60")])  # +50% in 3.5 months
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=MARKET, data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    setup_owner(c, clock)
    buy_fpt(c, clock)
    return c, clock


def test_a_large_buy_after_a_run_up_is_flagged_with_numbers(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/buy-check/fpt/300000000").json()  # 5 tr + 300 tr on 1 tỷ capital
    kinds = {f["kind"]: f for f in body["flags"]}
    assert kinds["ticker"]["weight"] == "0.3050" and kinds["ticker"]["limit"] == "0.25"
    assert kinds["fomo"]["change"] == "0.5000"
    assert body["symbol"] == "FPT" and body["amount"] == "300000000"


def test_a_small_buy_without_a_run_up_has_no_flags(tmp_path):
    c, clock = client(tmp_path)
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(2026, 10, 1), "58")])
    assert call(c, clock, "GET", "/internal/buy-check/FPT/10000000").json()["flags"] == []


def test_bad_input_is_refused(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/buy-check/FPT/abc").status_code == 422
    assert call(c, clock, "GET", "/internal/buy-check/FPT/-5").status_code == 422


def test_a_buy_that_pushes_the_stock_layer_over_its_target_is_flagged_with_the_bottom_up_rule(tmp_path):
    c, clock = client(tmp_path)  # Cân bằng 35%
    call(c, clock, "PUT", "/internal/equity-budget", {"layers": {"deposit": "50000000", "bond": "0", "gold": "0", "crypto": "0"}, "reserve": "0",
                                                     "expected_version": 0, "request_id": "eb1"})
    kinds = {f["kind"]: f for f in call(c, clock, "GET", "/internal/buy-check/FPT/90000000").json()["flags"]}
    assert "stocks_layer" in kinds and kinds["bottom_up"] == {"kind": "bottom_up", "short": "gold", "over": ["stocks"]}
