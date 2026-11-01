from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path, clock, repo=True):
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock,
                     personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()) if repo else None, data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def test_rows_criteria_and_saved_screens(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nHPG\n", encoding="utf-8")
    clock = Clock()
    c = client(tmp_path, clock)
    view = call(c, clock, "GET", "/internal/screener").json()
    assert [r["symbol"] for r in view["rows"]] == ["FPT", "HPG"] and view["screens"] == [] and view["version"] == 0
    assert view["criteria"]["verdict"] == {"label": "Định giá", "values": {"cheap": "Rẻ", "fair": "Hợp lý", "expensive": "Đắt"}}
    assert view["rows"][0]["missing"]["foreign20"] == "Chưa đủ 20 phiên khối ngoại (0)"
    saved = call(c, clock, "PUT", "/internal/screener", {"action": "save", "screen": {"name": "Rẻ", "criteria": {"verdict": ["cheap"]}, "notify": True},
                                                         "expected_version": 0, "request_id": "s1"}).json()
    assert saved["version"] == 1 and saved["screens"][0]["name"] == "Rẻ"
    bad = call(c, clock, "PUT", "/internal/screener", {"action": "save", "screen": {"name": "x", "criteria": {}}, "expected_version": 1,
                                                       "request_id": "s2"})
    assert bad.status_code == 422 and bad.json()["code"] == "criteria_required"


def test_without_personal_store_the_screener_is_unavailable(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, clock, repo=False), clock, "GET", "/internal/screener").status_code == 503
