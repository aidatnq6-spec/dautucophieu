from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path):
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock


def test_a_page_opened_is_counted_and_read_back(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "POST", "/internal/usage/visit", {"page": "/research/HPG"}).json() == {"page": "/research"}
    call(c, clock, "POST", "/internal/usage/visit", {"page": "/research"})
    out = call(c, clock, "GET", "/internal/usage").json()
    assert out["pages"][0]["page"] == "/research" and out["pages"][0]["last_30"] == 2 and out["slow"] == []


def test_a_path_that_is_not_a_page_is_refused(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "POST", "/internal/usage/visit", {"page": "../etc"}).status_code == 422
    assert call(c, clock, "GET", "/internal/usage").json()["pages"] == []


def test_a_request_slower_than_the_threshold_is_kept_masked(tmp_path, monkeypatch):
    from investment_agent.services import usage
    monkeypatch.setattr(usage, "SLOW_SECONDS", 0.0)  # every request counts as slow here
    c, clock = client(tmp_path)
    call(c, clock, "GET", "/internal/concentration/whatif/FPT/300000000")
    slow = call(c, clock, "GET", "/internal/usage").json()["slow"]
    assert [s["path"] for s in slow] == ["GET /internal/concentration/whatif/*/*"]  # the usage page itself is never counted
