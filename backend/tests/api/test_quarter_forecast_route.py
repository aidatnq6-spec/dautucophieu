from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.statements import StatementStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call

B = 10**9


def client(tmp_path, quarters):
    (tmp_path / "market-symbols.txt").write_text("HPG" + chr(10), encoding="utf-8")
    StatementStore(tmp_path / "statements").save({"symbol": "HPG", "fetched_at": "2026-11-07T00:00:00+00:00", "source": "vndirect:finfo",
                                                  "quarters": quarters, "years": {}})
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock


QUARTERS = {"2025-Q4": {"revenue": str(100 * B), "npat_parent": str(10 * B)}, "2026-Q3": {"revenue": str(130 * B)}}


def test_the_owner_saves_assumptions_for_the_next_quarter_and_gets_its_column(tmp_path):
    c, clock = client(tmp_path, QUARTERS)
    empty = call(c, clock, "GET", "/internal/quarter-forecast/HPG").json()
    assert empty["quarter"] == "2026-Q4" and empty["assumptions"] is None and empty["values"] == {} and empty["version"] == 0
    saved = call(c, clock, "PUT", "/internal/quarter-forecast/HPG/2026-Q4",
                 {"assumptions": {"revenue_yoy": "0.2", "gross_margin": "0.25"}, "expected_version": 0, "request_id": "f1"}).json()
    assert saved["version"] == 1 and saved["values"]["revenue"] == str(120 * B) and saved["values"]["gross_profit"] == str(30 * B)
    assert saved["values"]["pbt"] is None and saved["assumptions"] == {"revenue_yoy": "0.2", "gross_margin": "0.25"}


def test_a_forecast_for_a_quarter_now_reported_is_set_beside_the_actual_figures(tmp_path):
    c, clock = client(tmp_path, QUARTERS)
    call(c, clock, "PUT", "/internal/quarter-forecast/HPG/2026-Q4",
         {"assumptions": {"revenue_yoy": "0.2"}, "expected_version": 0, "request_id": "f1"})
    StatementStore(tmp_path / "statements").save({"symbol": "HPG", "fetched_at": "2027-02-01T00:00:00+00:00", "source": "vndirect:finfo",
                                                  "quarters": {**QUARTERS, "2026-Q4": {"revenue": str(110 * B)}}, "years": {}})
    body = call(c, clock, "GET", "/internal/quarter-forecast/HPG").json()
    assert body["quarter"] == "2027-Q1" and body["values"] == {}
    assert body["earlier"] == [{"quarter": "2026-Q4", "revenue": {"forecast": str(120 * B), "actual": str(110 * B)},
                                "npat_parent": {"forecast": None, "actual": None}}]


def test_assumptions_are_checked_and_only_the_next_quarter_takes_them(tmp_path):
    c, clock = client(tmp_path, QUARTERS)
    bad = call(c, clock, "PUT", "/internal/quarter-forecast/HPG/2026-Q4", {"assumptions": {"gross_margin": "1.5"}, "expected_version": 0, "request_id": "b1"})
    assert bad.status_code == 422 and "Biên gộp" in bad.json()["message"]
    assert call(c, clock, "PUT", "/internal/quarter-forecast/HPG/2026-Q4", {"assumptions": {"fin_income": "abc"}, "expected_version": 0,
                                                                          "request_id": "b2"}).status_code == 422
    assert call(c, clock, "PUT", "/internal/quarter-forecast/HPG/2027-Q2", {"assumptions": {"revenue_yoy": "0.1"}, "expected_version": 0,
                                                                          "request_id": "b3"}).status_code == 422
    assert call(c, clock, "GET", "/internal/quarter-forecast/ZZZ").status_code == 404
