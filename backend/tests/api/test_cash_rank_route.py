from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_cash_rank import data


def test_the_cash_ranking_and_the_cash_rich_on_the_macro_chain(tmp_path):
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=data(tmp_path))
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    body = call(c, clock, "GET", "/internal/market/cash-ranking").json()
    assert [r["symbol"] for r in body["rows"]] == ["AAA", "BBB", "CCC", "DDD"] and body["cash_rich_from"] == "0.20"
    chain = call(c, clock, "GET", "/internal/macro/chain").json()
    assert chain["cash_rich"] == [{"symbol": "AAA", "net_cash_to_cap": "0.2000", "quarter": "2026-Q3"}]
