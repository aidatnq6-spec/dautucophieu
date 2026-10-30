import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.insights.store import InsightStore
from investment_agent.market.corporate_events import EventStore
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.prices import PriceBar, PriceStore
from investment_agent.market.series import SeriesStore
from investment_agent.market.view import PricePoint, SyntheticMarket
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call  # Clock date: 2027-01-15
from test_events_route import ev
from test_insights_route import record


def bar(day: date, volume: int) -> PriceBar:
    return PriceBar(entity_id="FPT", session_date=day, open="10000", high="10000", low="10000", close="10000", volume=volume, currency="VND",
                    source_id="t", observed_at=datetime(2027, 1, 15, tzinfo=timezone.utc), provenance_mode="latest_restated", price_basis="adjusted")


def client_for(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"FPT": "Công nghệ Thông tin", "VCB": "Ngân hàng", "HPG": "Tài nguyên Cơ bản"}}),
                                              encoding="utf-8")
    years = {str(y): {"npat": "1000000000", "eps": "1000", "equity": "10000000000"} for y in range(2020, 2026)}
    quarters = {q: {"npat": "250000000", "equity": "10000000000"} for q in ("2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2")}
    FundamentalsStore(tmp_path / "fundamentals").save({"symbol": "FPT", "fetched_at": "2026-10-26T00:00:00+00:00", "source": "t",
                                                      "years": years, "quarters": quarters, "issues": [],
                                                      "dividends": [{"date": f"{y}-07-01", "cash": "500"} for y in range(2021, 2027)]})
    # Closes in thousand đồng: 8 a year ago (outside 52 weeks), then 15 and 9, then 11 and 12 as the last two sessions.
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(2025, 12, 1), "8"), (datetime(2026, 3, 2), "15"), (datetime(2026, 6, 1), "9"),
                                                             (datetime(2027, 1, 13), "11"), (datetime(2027, 1, 14), "12")])
    first = date(2026, 12, 1)
    PriceStore(tmp_path).write_revision("FPT", "r1", [bar(first + timedelta(days=i), 1000 * (i + 1)) for i in range(25)])
    EventStore(tmp_path).save("FPT", [ev(1, "FPT", "dividend_cash", "2027-01-20"), ev(2, "FPT", "meeting", "2026-04-10"),
                                      ev(3, "FPT", "insider", "2027-01-12"), ev(4, "FPT", "issue", None)], fetched_at="2027-01-15T15:40:00+07:00")
    EventStore(tmp_path).save("VCB", [ev(1, "VCB", "meeting", "2027-01-18")], fetched_at="2027-01-15T15:40:00+07:00")
    store = InsightStore(tmp_path / "insights")
    store.save(record("a", "2027-01-01", "favourable", [("Công nghệ Thông tin", "benefit"), ("Ngân hàng", "harm")]))
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=SyntheticMarket(prices={"FPT": PricePoint(Decimal(12000), date(2027, 1, 14))}), data_dir=tmp_path)
    client = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    return lambda path: call(client, clock, "GET", path)


def test_stock_profile_gathers_facts_valuation_events_and_sector_insights(tmp_path):
    get = client_for(tmp_path)
    body = get("/internal/stock/fpt").json()
    assert (body["symbol"], body["sector"], body["watched"], body["held"]) == ("FPT", "Công nghệ Thông tin", True, False)
    f = body["facts"]
    assert (f["price"], f["price_date"], f["change_pct"]) == ("12000", "2027-01-14", "0.0909")
    assert (f["high_52w"], f["low_52w"]) == ("15000", "9000")  # the close of 2025-12-01 is more than 52 weeks back
    assert f["shares"] == 1000000 and f["market_cap"] == "12000000000"
    assert (f["avg_volume"], f["avg_volume_sessions"]) == (15500, 20)  # the last 20 of 25 sessions: 6,000 … 25,000
    assert body["valuation"]["symbol"] == "FPT" and body["valuation"]["methods"]
    assert all(isinstance(m["value"], (str, type(None))) for m in body["valuation"]["methods"])
    assert [e["id"] for e in body["events"]["upcoming"]] == ["FPT-1"]
    assert [e["id"] for e in body["events"]["past"]] == ["FPT-2"]
    assert [e["id"] for e in body["events"]["undated"]] == ["FPT-4"] and [e["id"] for e in body["events"]["insider"]] == ["FPT-3"]
    assert body["insights"]["sector"]["sector"] == "Công nghệ Thông tin" and body["insights"]["sector"]["benefit"] == 1
    assert body["insights"]["window_days"] == 60


def test_stock_profile_outside_the_watchlist_shows_what_is_known(tmp_path):
    body = client_for(tmp_path)("/internal/stock/HPG").json()
    assert (body["watched"], body["sector"], body["valuation"]) == (False, "Tài nguyên Cơ bản", None)
    assert body["facts"]["price"] is None and body["facts"]["market_cap"] is None and body["facts"]["avg_volume"] is None
    assert body["events"] == {"upcoming": [], "past": [], "undated": [], "insider": []} and body["insights"]["sector"] is None


def test_stock_profile_rejects_a_malformed_symbol(tmp_path):
    assert client_for(tmp_path)("/internal/stock/..%2Fx").status_code in (400, 404)
