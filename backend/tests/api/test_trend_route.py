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
