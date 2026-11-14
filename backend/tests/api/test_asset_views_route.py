from datetime import datetime

from investment_agent.market.series import SeriesStore

from signed_client import call
from test_deposit_book_route import client, save_book  # ledger: 100 tr deposited 04/01/2027, FPT 100 × 50,000 on 05/01; FPT at 60,000 on 14/01


def test_the_asset_map_puts_the_stocks_cash_and_book_rows_in_layers(tmp_path):
    c, clock = client(tmp_path)
    save_book(c, clock)
    body = call(c, clock, "GET", "/internal/asset-map").json()
    groups = {g["id"]: g for g in body["groups"]}
    assert groups["stocks"]["tiles"] == [{"id": "stock:FPT", "label": "FPT", "note": None, "value": "6000000", "change": "0.2"}]
    assert groups["deposits"]["value"] == "300000000" and groups["cash"]["value"] == "110000000"  # 95 tr ledger + 15 tr accounts
    assert body["unpriced"] == []


def test_the_month_bridge_explains_the_account_s_month_to_the_dong(tmp_path):
    store = SeriesStore(tmp_path / "trend-sources")
    store.upsert("VNINDEX-1d", [(datetime(2027, 1, d), "1700") for d in (4, 5, 6, 7, 8, 11, 12, 13, 14)])
    store.upsert("FPT-1d", [(datetime(2027, 1, d), "60") for d in (5, 6, 7, 8, 11, 12, 13, 14)])
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/month-bridge").json()
    assert body["months"] == ["2027-01"]
    b = body["bridge"]
    assert b["status"] == "ok" and b["start"] == "0" and b["end"] == "101000000" and b["other"] == "0" and b["end_day"] == "2027-01-14"
    assert b["steps"] == [{"id": "flows", "amount": "100000000"}, {"id": "ticker:FPT", "symbol": "FPT", "amount": "1000000"}]
    assert body["book"] is None  # no Sổ tài sản saved
    assert call(c, clock, "GET", "/internal/month-bridge/2027-13").status_code == 422


def test_the_daily_calendar_gives_each_session_s_gain(tmp_path):
    store = SeriesStore(tmp_path / "trend-sources")
    store.upsert("VNINDEX-1d", [(datetime(2027, 1, d), "1700") for d in (5, 6, 7)])
    store.upsert("FPT-1d", [(datetime(2027, 1, 5), "50"), (datetime(2027, 1, 6), "55"), (datetime(2027, 1, 7), "54")])
    c, clock = client(tmp_path)
    days = call(c, clock, "GET", "/internal/performance-daily").json()["days"]
    assert [(d["date"], d["gain"]) for d in days] == [("2027-01-06", "500000"), ("2027-01-07", "-100000")]


def test_the_month_bridge_adds_the_book_as_saved_by_the_end_of_the_month(tmp_path):
    store = SeriesStore(tmp_path / "trend-sources")
    store.upsert("VNINDEX-1d", [(datetime(2027, 1, d), "1700") for d in (4, 5, 14)])
    store.upsert("FPT-1d", [(datetime(2027, 1, d), "60") for d in (5, 14)])
    c, clock = client(tmp_path)
    save_book(c, clock)  # stamped by the store's own clock, before the end of January 2027
    book = call(c, clock, "GET", "/internal/month-bridge").json()["book"]
    assert book["status"] == "ok" and book["start"] == "0" and book["end"] == "315000000"  # deposits 300 tr + accounts 15 tr
    assert book["steps"] == [{"id": "book:entries", "amount": "315000000"}]


def test_the_book_is_read_as_it_stood_at_a_moment(tmp_path):
    from datetime import timedelta, timezone

    from investment_agent.api.auth import OwnerContext
    from investment_agent.services.deposit_book import book_at
    c, clock = client(tmp_path)
    save_book(c, clock)
    repo, owner = c.app.state.personal_repository, OwnerContext(uid="owner-1", role="owner", correlation_id="t")
    assert book_at(repo, owner, datetime.now(timezone.utc) - timedelta(days=1)) is None  # saved just now: not yet a day ago
    assert len(book_at(repo, owner, datetime.now(timezone.utc) + timedelta(minutes=1)).deposits) == 2
