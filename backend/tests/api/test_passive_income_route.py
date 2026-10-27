from datetime import date

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.leading import MacroStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_overview_route import MARKET, buy_fpt, setup_owner  # Cân bằng; 95 tr cash + 5 tr FPT at cost in the ledger


def client(tmp_path):
    MacroStore(tmp_path).upsert("deposit_12m", [(date(2027, 1, 14), "6")], entry="auto")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=MARKET, data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    setup_owner(c, clock)
    buy_fpt(c, clock)
    return c, clock


def test_no_goal_yet_offers_the_deposit_rate_as_the_default(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/passive-income").json()
    assert body == {"version": 0, "goal": None, "default_rate": "6", "result": None, "capital": None, "contribution": "0"}


def test_the_goal_uses_the_pyramid_capital_the_monthly_plan_and_the_default_rate(tmp_path):
    c, clock = client(tmp_path)
    call(c, clock, "PUT", "/internal/equity-budget", {"layers": {"deposit": "900000000", "bond": "0", "gold": "0", "crypto": "0"}, "reserve": "0",
                                                     "expected_version": 0, "request_id": "eb1"})
    call(c, clock, "PUT", "/internal/contributions", {"amount": "8000000", "day": 10, "start": "2027-02", "expected_version": 0, "request_id": "cp1"})
    assert call(c, clock, "PUT", "/internal/passive-income", {"target": "5000000", "rate": None, "expected_version": 0, "request_id": "pi1"}).status_code == 200
    body = call(c, clock, "GET", "/internal/passive-income").json()
    assert body["capital"] == "1000000000" and body["contribution"] == "8000000"   # 900 tr deposits + 95 tr cash + 5 tr stocks
    assert body["result"]["required"] == "1000000000" and body["result"]["months"] == 0  # 5 tr × 12 / 6%


def test_bad_goals_are_refused(tmp_path):
    c, clock = client(tmp_path)
    for goal in ({"target": "0", "rate": None}, {"target": "abc", "rate": None}, {"target": "1000000", "rate": "0"}, {"target": "1000000", "rate": "60"}):
        assert call(c, clock, "PUT", "/internal/passive-income", {**goal, "expected_version": 0, "request_id": "pi2"}).status_code == 422
