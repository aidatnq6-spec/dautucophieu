import json
from datetime import date, datetime, timedelta

from investment_agent.market.leading import MacroStore
from investment_agent.market.omo import OmoStore
from investment_agent.market.series import SeriesStore

from signed_client import call
from test_deposit_book_route import client


def test_liquidity_brings_the_central_rate_the_open_market_and_the_monthly_trade_figures(tmp_path):
    store = MacroStore(tmp_path)
    store.upsert("usd_vnd_central", [(date(2027, 1, 2), "25000"), (date(2027, 1, 15), "25100")], entry="auto")
    store.upsert("usd_vnd_vcb", [(date(2027, 1, 14), "26300")], entry="auto")
    store.upsert("vn_interbank_on", [(date(2027, 1, 14), "4.2")], entry="auto")
    store.upsert("vn_trade_balance", [(date(2026, 12, 31), "-1.5")], entry="auto")
    store.upsert("vn_fdi_disbursed", [(date(2026, 12, 31), "25")], entry="auto")
    OmoStore(tmp_path).upsert({"date": "2027-01-14", "total": "500", "rows": [{"kind": "repo", "group": "Mua kỳ hạn", "term_days": 7,
                                                                             "members": "3/3", "volume": "500", "rate": "4.5"}]})
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/macro/liquidity").json()
    assert body["fx"]["ceiling"] == "26355" and body["fx"]["near_ceiling"] is True and body["fx"]["ytd"]["change"] == "0.004"
    assert body["omo"]["latest"]["inject"] == "500" and body["omo"]["complete"] is False
    assert body["interbank"]["terms"][0] == {"id": "vn_interbank_on", "date": "2027-01-14", "value": "4.2"}
    assert body["external"]["vn_trade_balance"] == {"date": "2026-12-31", "value": "-1.5"} and body["external"]["vn_trade_balance_ytd"] is None


def test_the_chain_lists_the_held_tickers_whose_sector_moves_with_rates(tmp_path):
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2027-01-01", "sectors": {"FPT": "Ngân hàng"}}), encoding="utf-8")
    c, clock = client(tmp_path)  # holds FPT
    body = call(c, clock, "GET", "/internal/macro/chain").json()
    assert body["rate_sensitive"] == [{"symbol": "FPT", "sector": "Ngân hàng"}]
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2027-01-01", "sectors": {"FPT": "Công nghệ Thông tin"}}), encoding="utf-8")
    assert call(c, clock, "GET", "/internal/macro/chain").json()["rate_sensitive"] == []
