from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def test_the_receivable_signs_board(tmp_path):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))
    from test_receivable_signs import data
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=data(tmp_path))
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    body = call(c, clock, "GET", "/internal/market/receivable-signs").json()
    assert [r["symbol"] for r in body["rows"]] == ["AAA", "BBB", "VCB"] and [s["key"] for s in body["signs"]][0] == "other_receivables"
