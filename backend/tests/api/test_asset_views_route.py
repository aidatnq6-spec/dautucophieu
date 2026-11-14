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
    assert call(c, clock, "GET", "/internal/month-bridge?month=2027-13").status_code == 422
