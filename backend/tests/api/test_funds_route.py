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
    assert body["funds"][0]["score"] == {"score": None, "parts": {"returns": None, "fee": None, "risk": None}, "counted": [], "risk_days": 1,
                                         "peers": 1, "trend": None}  # alone in its kind: no score


def test_without_a_sync_the_board_is_empty_not_guessed(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/funds").json()
    assert body["funds"] == [] and body["mine"]["groups"] == [] and body["source"] is None


def test_stocks_held_through_funds_add_to_those_held_directly_and_the_stock_page_names_the_funds(tmp_path):
    from investment_agent.market.fund_holdings import FundHoldingsStore
    seed(tmp_path)
    FundHoldingsStore(tmp_path).save({"source": "Fmarket", "fetched_at": "2026-11-14T00:00:00+00:00", "funds": {
        "VFF": {"as_of": "2026-10", "stocks": [{"symbol": "FPT", "percent": "10", "industry": "x"}], "bonds": [], "assets": [], "industries": []}}})
    c, clock = client(tmp_path)  # FPT 100 shares at 60,000 held directly
    save_book(c, clock, bonds=[{"id": "f1", "name": "Quỹ B", "amount": "900", "fund": "VFF", "units": "50"}])
    through = call(c, clock, "GET", "/internal/funds").json()["through"]
    assert through["rows"] == [{"symbol": "FPT", "direct": "6000000", "through": "100", "total": "6000100", "share": "0.9999",
                                "funds": [{"code": "VFF", "percent": "10"}]}]
    assert through["covered"] == {"VFF": {"as_of": "2026-10", "stocks": "10", "bonds": "0"}} and through["unpriced"] == []
    body = call(c, clock, "GET", "/internal/funds/holding/fpt").json()
    assert body == {"symbol": "FPT", "funds": [{"code": "VFF", "name": "Quỹ trái phiếu B", "percent": "10", "as_of": "2026-10", "amount": "100"}],
                    "fund_rows": 1}
    assert call(c, clock, "GET", "/internal/funds/holding/HPG").json()["funds"] == []


def test_the_score_trend_is_against_the_month_before_not_this_month_s_own_snapshot(tmp_path):
    from investment_agent.domain.fund_score import record_scores
    rows = [{**FUND_ROWS[0], "shortName": code, "productNavChange": {"navTo12Months": m12}} for code, m12 in (("DCDS", 5), ("DCAF", 1))]
    fund_nav_sync(FundNavStore(tmp_path), post=lambda u, b: {"data": {"rows": rows}}, now=datetime(2026, 11, 14, tzinfo=timezone.utc))
    c, clock = client(tmp_path)  # today 2027-01-15 in the fixture clock
    record_scores(tmp_path, "2026-12", {"DCDS": {"score": "40"}})
    record_scores(tmp_path, "2027-01", {"DCDS": {"score": "100"}})
    dcds = next(f for f in call(c, clock, "GET", "/internal/funds").json()["funds"] if f["code"] == "DCDS")
    assert dcds["score"]["score"] == "75" and dcds["score"]["trend"] == {"previous": "40", "change": "35"}
