import json

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.statements import StatementStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("HPG" + chr(10), encoding="utf-8")
    StatementStore(tmp_path / "statements").save({"symbol": "HPG", "fetched_at": "2026-11-07T00:00:00+00:00", "source": "vndirect:finfo",
                                                  "quarters": {"2026-Q1": {"revenue": "50000000000000"}}, "years": {}})
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock


def test_the_owner_saves_a_year_s_plan_with_its_source_and_sees_the_progress(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/annual-plans/HPG").json() == {"symbol": "HPG", "version": 0, "plans": []}
    saved = call(c, clock, "PUT", "/internal/annual-plans/HPG/2026", {"revenue": "200000", "profit": "", "profit_kind": "npat",
                                                                     "source": "Nghị quyết ĐHCĐ 2026", "expected_version": 0, "request_id": "p1"}).json()
    assert saved["version"] == 1 and saved["plans"][0]["year"] == "2026" and saved["plans"][0]["revenue"]["ratio"] == "0.2500"
    assert saved["plans"][0]["profit"] is None and saved["plans"][0]["through"] == "2026-Q1"
    gone = call(c, clock, "POST", "/internal/annual-plans/HPG/2026/delete", {"expected_version": 1, "request_id": "p2"}).json()
    assert gone["plans"] == [] and gone["version"] == 2


def test_a_plan_needs_a_figure_a_source_and_a_watched_ticker(tmp_path):
    c, clock = client(tmp_path)
    body = {"revenue": "", "profit": "", "profit_kind": "npat", "source": "x y z", "expected_version": 0, "request_id": "q1"}
    assert call(c, clock, "PUT", "/internal/annual-plans/HPG/2026", body).json()["message"] == "Nhập ít nhất doanh thu hoặc lợi nhuận kế hoạch."
    body.update(revenue="-5", request_id="q2")
    assert call(c, clock, "PUT", "/internal/annual-plans/HPG/2026", body).status_code == 422
    body.update(revenue="1000", source=" ", request_id="q3")
    assert call(c, clock, "PUT", "/internal/annual-plans/HPG/2026", body).status_code == 422  # the source is required
    body.update(source="Nghị quyết", request_id="q4")
    assert call(c, clock, "PUT", "/internal/annual-plans/HPG/26", body).status_code == 422
    assert call(c, clock, "PUT", "/internal/annual-plans/ZZZ/2026", body).status_code == 404
    stale = call(c, clock, "PUT", "/internal/annual-plans/HPG/2026", {**body, "expected_version": 3, "request_id": "q5"})
    assert stale.status_code == 409
