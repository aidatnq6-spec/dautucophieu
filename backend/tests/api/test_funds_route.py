from datetime import datetime, timezone

from investment_agent.market.fund_nav import FundNavStore, fund_nav_sync
from investment_agent.market.series import SeriesStore

from signed_client import call
from test_deposit_book_route import client, save_book

FUND_ROWS = [{"shortName": "DCDS", "name": "Quỹ cổ phiếu A", "nav": 100, "extra": {"lastNAVDate": 1794502800000}, "managementFee": 1.95,
              "owner": {"shortName": "M"}, "dataFundAssetType": {"code": "STOCK"}, "productNavChange": {"navTo12Months": -9.64, "navToLastYear": -14.19}},
             {"shortName": "VFF", "name": "Quỹ trái phiếu B", "nav": 20, "extra": {"lastNAVDate": 1794502800000}, "managementFee": 0.95,
              "owner": {"shortName": "V"}, "dataFundAssetType": {"code": "BOND"}, "productNavChange": {"navTo12Months": 6.1}}]


def seed(tmp_path):
    fund_nav_sync(FundNavStore(tmp_path), post=lambda u, b: {"data": {"rows": FUND_ROWS}}, now=datetime(2026, 11, 14, tzinfo=timezone.utc))
    SeriesStore(tmp_path / "trend-sources").upsert("VNINDEX-1d", [(datetime(2025, 11, 13), "1600"), (datetime(2026, 11, 13), "1734.93")])


def test_the_board_lists_every_fund_with_benchmarks_and_the_owners_split(tmp_path):
    seed(tmp_path)
    c, clock = client(tmp_path)
    save_book(c, clock, bonds=[{"id": "f1", "name": "Quỹ B", "amount": "900", "fund": "VFF", "units": "50"}])
    body = call(c, clock, "GET", "/internal/funds").json()
    assert [f["code"] for f in body["funds"]] == ["DCDS", "VFF"] and [f["held"] for f in body["funds"]] == [False, True]
    assert body["benchmark"]["deposit_12m"] == "5" and body["benchmark"]["vnindex"]["m12"] == "8.43"
    assert body["mine"]["groups"] == [{"kind": "BOND", "value": "1000", "share": "1", "funds": ["VFF"]}]
    assert body["mine"]["notes"] == ["fewer_than_3", "single_kind"]
    assert body["source"] == {"name": "Fmarket", "fetched_at": "2026-11-14T00:00:00+00:00"} and body["history_days"] == {"DCDS": 1, "VFF": 1}


def test_without_a_sync_the_board_is_empty_not_guessed(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/funds").json()
    assert body["funds"] == [] and body["mine"]["groups"] == [] and body["source"] is None
