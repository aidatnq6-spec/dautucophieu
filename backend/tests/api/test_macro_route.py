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


def test_rate_cycle_uses_the_us_as_a_labelled_reference_until_vietnam_has_six_months(tmp_path):
    clock = Clock()  # 2027-01-15
    store = MacroStore(tmp_path)
    store.upsert("deposit_12m", [(date(2026, 10, 25), "5.63"), (date(2027, 1, 14), "5.60")], entry="auto")
    store.upsert("fed_effr", [(date(2026, 7, 1), "4.33"), (date(2027, 1, 14), "3.80")], entry="auto")
    store.upsert("us10y", [(date(2026, 7, 1), "4.40"), (date(2027, 1, 14), "4.30")], entry="auto")
    body = call(client(tmp_path, clock), clock, "GET", "/internal/macro/cycle").json()
    assert body["basis"] == "us_reference" and body["phase"] == "down"
    assert body["vietnam_since"] == "2026-10-25" and body["vietnam_ready_on"] == "2027-04-25"


def test_macro_chain_reads_the_stored_series_and_the_vn_index(tmp_path):
    from datetime import datetime
    from investment_agent.market.series import SeriesStore
    clock = Clock()  # 2027-01-15
    store = MacroStore(tmp_path)
    store.upsert("wti", [(date(2026, 12, 1), "100"), (date(2027, 1, 14), "90")], entry="auto")
    store.upsert("foreign_net", [(date(2027, 1, 13), "300"), (date(2027, 1, 14), "120.5")], entry="auto")
    SeriesStore(tmp_path / "trend-sources").upsert("VNINDEX-1d", [(datetime(2026, 12, 10), "1600"), (datetime(2027, 1, 14), "1700")])
    body = call(client(tmp_path, clock), clock, "GET", "/internal/macro/chain").json()
    n = {x["id"]: x for x in body["nodes"]}
    assert (n["oil"]["direction"], n["oil"]["effect"]) == ("down", "support")
    assert (n["foreign"]["direction"], n["foreign"]["latest"]["value"]) == ("buy", "420.5")
    assert (n["vnindex"]["direction"], n["vnindex"]["latest"]["value"]) == ("up", "1700")
    assert body["missing"] == ["inflation", "rates"]
