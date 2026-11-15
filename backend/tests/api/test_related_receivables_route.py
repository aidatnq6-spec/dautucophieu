from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("VJC" + chr(10), encoding="utf-8")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock


def row(name, amount, grouped=False):
    terms = None if grouped else False  # a grouped line in the notes gives no terms
    return {"name": name, "amount": amount, "grouped": grouped, "related": True, "secured": terms, "interest": terms, "collect_within": None}


def test_the_owner_keeps_related_receivables_year_by_year_and_sees_what_vanished(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/related-receivables/VJC").json() == {"symbol": "VJC", "version": 0, "years": [], "findings": []}
    one = call(c, clock, "PUT", "/internal/related-receivables/VJC/2019", {"source": "BCTC 2019, TM 7", "rows": [row("Công ty Alpha", "2820")],
                                                                          "expected_version": 0, "request_id": "rr1"}).json()
    assert one["version"] == 1 and one["years"][0]["year"] == "2019"
    two = call(c, clock, "PUT", "/internal/related-receivables/VJC/2020", {"source": "BCTC 2020, TM 38", "rows": [row("Bên liên quan khác", "2953", True)],
                                                                          "expected_version": 1, "request_id": "rr2"}).json()
    assert [f["kind"] for f in two["findings"]] == ["vanished"] and two["findings"][0]["group"]["name"] == "Bên liên quan khác"
    gone = call(c, clock, "POST", "/internal/related-receivables/VJC/2020/delete", {"expected_version": 2, "request_id": "rr3"}).json()
    assert [y["year"] for y in gone["years"]] == ["2019"] and gone["findings"][0]["kind"] == "unsecured_free"


def test_a_year_is_refused_without_a_source_for_an_unwatched_ticker_or_a_bad_year(tmp_path):
    c, clock = client(tmp_path)
    bad = call(c, clock, "PUT", "/internal/related-receivables/VJC/2020", {"source": " ", "rows": [row("A", "1")], "expected_version": 0, "request_id": "rs1"})
    assert bad.status_code == 422 and bad.json()["code"] == "invalid_source"
    assert call(c, clock, "PUT", "/internal/related-receivables/VJC/20x0", {"source": "BCTC", "rows": [row("A", "1")], "expected_version": 0,
                                                                           "request_id": "rs2"}).status_code == 422
    assert call(c, clock, "GET", "/internal/related-receivables/FPT").status_code == 404
