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
    assert len(rows) == 28 and rows["us10y"]["assessment"] == "Xấu" and rows["vn_pmi"]["value"] is None


def test_owner_enters_a_manual_value_with_its_source(tmp_path):
    clock = Clock()
    c = client(tmp_path, clock)
    r = call(c, clock, "POST", "/internal/macro/vn_pmi/observations", {"month": "2026-10", "value": "51,9", "source_url": "https://example.vn/pmi"})
    assert r.status_code == 200 and r.json() == {"indicator": "vn_pmi", "date": "2026-10-31", "value": "51.9"}  # a monthly figure: the month's end
    assert MacroStore(tmp_path).read("vn_pmi")[-1]["entry"] == "manual"


def test_a_monthly_figure_is_entered_by_month_never_by_the_day_it_was_typed(tmp_path):
    clock = Clock()  # 2027-01-15
    c = client(tmp_path, clock)
    by_day = call(c, clock, "POST", "/internal/macro/vn_pmi/observations", {"date": "2026-10-25", "value": "51,9"})
    assert by_day.status_code == 422 and by_day.json()["code"] == "month_required"
    assert call(c, clock, "POST", "/internal/macro/vn_pmi/observations", {"month": "2027-01", "value": "51"}).json()["code"] == "future_date"  # not over yet
    assert call(c, clock, "POST", "/internal/macro/vn_pmi/observations", {"month": "2026-13", "value": "51"}).status_code == 422
    daily = call(c, clock, "POST", "/internal/macro/deposit_12m/observations", {"month": "2026-10", "value": "5"})
    assert daily.status_code == 422 and daily.json()["code"] == "date_required"  # a daily figure keeps its day
    rows = {r["id"]: r for r in call(c, clock, "GET", "/internal/macro").json()["rows"]}
    assert rows["vn_pmi"]["period"] == "month" and rows["deposit_12m"]["period"] is None


def test_manual_entry_is_refused_for_automatic_or_unknown_indicators_and_bad_input(tmp_path):
    clock = Clock()
    c = client(tmp_path, clock)
    assert call(c, clock, "POST", "/internal/macro/us10y/observations", {"date": "2026-10-01", "value": "4"}).status_code == 409
    assert call(c, clock, "POST", "/internal/macro/nope/observations", {"date": "2026-10-01", "value": "4"}).status_code == 404
    assert call(c, clock, "POST", "/internal/macro/vn_pmi/observations", {"month": "2099-01", "value": "4"}).status_code == 422
    assert call(c, clock, "POST", "/internal/macro/vn_pmi/observations", {"month": "2026-10", "value": "abc"}).status_code == 422
    assert call(c, clock, "POST", "/internal/macro/vn_pmi/observations",
                {"month": "2026-10", "value": "4", "source_url": "javascript:alert(1)"}).status_code == 422


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
    assert body["missing"] == ["inflation", "liquidity", "rates"]
    assert body["cash_rich"] == []  # no watched ticker with statements here



def test_a_session_figure_is_refused_on_a_day_without_a_session_with_the_nearest_one_named(tmp_path):
    clock = Clock()  # 2027-01-15
    c = client(tmp_path, clock)
    sunday = call(c, clock, "POST", "/internal/macro/vn10y/observations", {"date": "2026-10-25", "value": "4,58"})
    assert sunday.status_code == 422 and sunday.json()["code"] == "not_a_session"
    assert sunday.json()["message"] == "Ngày 25/10/2026 là ngày nghỉ, không có phiên giao dịch: chọn phiên gần nhất (23/10/2026)."
    holiday = call(c, clock, "POST", "/internal/macro/vn_interbank_on/observations", {"date": "2026-09-02", "value": "4"})
    assert holiday.json()["code"] == "not_a_session" and "28/08/2026" in holiday.json()["message"]  # 31/8–2/9 off on HOSE's calendar
    assert call(c, clock, "POST", "/internal/macro/vn10y/observations", {"date": "2026-10-23", "value": "4,49"}).status_code == 200
    # a year without HOSE's calendar: weekends only
    assert call(c, clock, "POST", "/internal/macro/vn10y/observations", {"date": "2027-01-09", "value": "4"}).json()["message"].endswith("(08/01/2027).")
    assert call(c, clock, "POST", "/internal/macro/vn10y/observations", {"date": "2027-01-11", "value": "4"}).status_code == 200
    # the central rate is published on weekends too: not checked
    assert call(c, clock, "POST", "/internal/macro/usd_vnd_central/observations", {"date": "2026-10-25", "value": "25100"}).status_code == 200
    rows = {r["id"]: r for r in call(c, clock, "GET", "/internal/macro").json()["rows"]}
    assert rows["vn10y"]["period"] == "session" and rows["usd_vnd_central"]["period"] is None
