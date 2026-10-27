from datetime import date

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.leading import MacroStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path, clock, repo=True):
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock,
                     personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()) if repo else None, data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def test_macro_lists_every_indicator(tmp_path):
    clock = Clock()
    MacroStore(tmp_path).upsert("us10y", [(date(2026, 10, 21), "4.91"), (date(2026, 10, 23), "4.96")], entry="auto")
    body = call(client(tmp_path, clock), clock, "GET", "/internal/macro").json()
    rows = {r["id"]: r for r in body["rows"]}
    assert len(rows) == 17 and rows["us10y"]["assessment"] == "Xấu" and rows["vn_pmi"]["value"] is None


def test_owner_enters_a_manual_value_with_its_source(tmp_path):
    clock = Clock()
    c = client(tmp_path, clock)
    r = call(c, clock, "POST", "/internal/macro/vn_pmi/observations", {"date": "2026-10-01", "value": "51,9", "source_url": "https://example.vn/pmi"})
    assert r.status_code == 200 and r.json()["value"] == "51.9"
    assert MacroStore(tmp_path).read("vn_pmi")[-1]["entry"] == "manual"


def test_manual_entry_is_refused_for_automatic_or_unknown_indicators_and_bad_input(tmp_path):
    clock = Clock()
    c = client(tmp_path, clock)
    assert call(c, clock, "POST", "/internal/macro/us10y/observations", {"date": "2026-10-01", "value": "4"}).status_code == 409
    assert call(c, clock, "POST", "/internal/macro/nope/observations", {"date": "2026-10-01", "value": "4"}).status_code == 404
    assert call(c, clock, "POST", "/internal/macro/vn_pmi/observations", {"date": "2099-01-01", "value": "4"}).status_code == 422
    assert call(c, clock, "POST", "/internal/macro/vn_pmi/observations", {"date": "2026-10-01", "value": "abc"}).status_code == 422
    assert call(c, clock, "POST", "/internal/macro/vn_pmi/observations",
                {"date": "2026-10-01", "value": "4", "source_url": "javascript:alert(1)"}).status_code == 422


def test_macro_without_personal_store_is_unavailable(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, clock, repo=False), clock, "GET", "/internal/macro").status_code == 503


def test_scraped_indicators_also_accept_a_manual_value(tmp_path):
    clock = Clock()
    c = client(tmp_path, clock)
    assert call(c, clock, "POST", "/internal/macro/deposit_12m/observations", {"date": "2026-10-01", "value": "9,55"}).status_code == 200
