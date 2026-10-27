from datetime import date, datetime

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings, OwnerContext
from investment_agent.domain.journal import JournalEntry
from investment_agent.market.corporate_events import EventStore
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.journal import append_entry

from signed_client import SECRET, TOKEN, Clock, call  # Clock date: 2027-01-15
from test_events_route import ev
from test_overview_route import MARKET, buy_fpt, setup_owner  # MARKET prices FPT at 60,000; FPT bought 100 × 50,000 on 2027-01-05


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nMBB\n", encoding="utf-8")
    series = SeriesStore(tmp_path / "trend-sources")
    series.upsert("FPT-1d", [(datetime(2027, 1, 13), "59"), (datetime(2027, 1, 14), "60")])  # thousand đồng
    series.upsert("VNINDEX-1d", [(datetime(2027, 1, 13), "1240"), (datetime(2027, 1, 14), "1252.4")])
    EventStore(tmp_path).save("FPT", [ev(1, "FPT", "dividend_cash", "2027-01-19", "Cổ tức tiền 2.000 đ"), ev(2, "FPT", "meeting", "2027-03-01")],
                              fetched_at="2027-01-15T07:00:00+07:00")
    EventStore(tmp_path).save("MBB", [ev(1, "MBB", "meeting", "2027-01-16")], fetched_at="2027-01-15T07:00:00+07:00")  # not held
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=MARKET, data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    setup_owner(c, clock)
    buy_fpt(c, clock)
    return c, clock


def test_quick_numbers_for_the_last_session(tmp_path):
    c, clock = client(tmp_path)
    g = call(c, clock, "GET", "/internal/glance").json()
    assert g["session_date"] == "2027-01-14"
    k = g["kpis"]
    assert k["market_value"] == "6000000" and k["unrealized_gain"] == "1000000"
    assert k["day_change"] == "100000" and k["day_change_ratio"] == "0.0169"  # 100 × (60,000 − 59,000) on 5.9 triệu
    assert k["vnindex"] == "1252.4" and k["vnindex_change_ratio"] == "0.0100"
    assert k["room"] is None  # no total financial assets entered yet


def test_attention_gathers_events_concentration_and_journal_reviews(tmp_path):
    c, clock = client(tmp_path)
    call(c, clock, "PUT", "/internal/settings/portfolio", {"settings": {"concentration_limit": "0.004"}, "expected_version": 0, "request_id": "pf1"})
    append_entry(c.app.state.personal_repository, OwnerContext("owner-1", "owner", "test"),
                 JournalEntry(entry_id="j1", symbol="FPT", kind="buy", created_on=date(2027, 1, 5), reason="KQKD tốt", context={"price": "50000"}),
                 request_id="j1")
    a = call(c, clock, "GET", "/internal/glance").json()["attention"]
    assert [(e["symbol"], e["key_date"]) for e in a["events"]] == [("FPT", "2027-01-19")]  # held only, within 5 days
    assert [o["name"] for o in a["over_limit"]] == ["FPT"]
    assert [(j["symbol"], j["change"]) for j in a["journal_reviews"]] == [("FPT", "0.2000")]  # recorded at 50,000, now 60,000
    assert a["latest_report"] is None


def test_nothing_to_watch_is_said_plainly(tmp_path):
    c, clock = client(tmp_path)
    EventStore(tmp_path).save("FPT", [], fetched_at="2027-01-15T07:00:00+07:00")
    a = call(c, clock, "GET", "/internal/glance").json()["attention"]
    assert a["events"] == [] and a["over_limit"] == [] and a["journal_reviews"] == []
