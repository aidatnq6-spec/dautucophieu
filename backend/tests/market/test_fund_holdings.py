import json
from datetime import datetime, timezone

from investment_agent.market.fund_holdings import FundHoldingsStore, fund_holdings, fund_holdings_sync

NOW = datetime(2026, 11, 14, 13, tzinfo=timezone.utc)


def listing(*rows):
    return {"data": {"rows": [{"id": i, "shortName": code, "productFund": {"updateAssetHoldingTime": month}} for i, code, month in rows]}}


def detail(code):
    return {"data": {"shortName": code,
                     "productTopHoldingList": [{"stockCode": "VIC", "industry": "Bất động sản", "type": "STOCK", "netAssetPercent": 11.75},
                                               {"stockCode": "TCB", "industry": "Ngân hàng", "type": "STOCK", "netAssetPercent": 6.98}],
                     "productTopHoldingBondList": [{"stockCode": "VHM12612", "industry": "Bất động sản", "type": "UNLISTED_BOND", "netAssetPercent": 12.41}],
                     "productAssetHoldingList": [{"assetType": {"code": "STOCK", "name": "Cổ phiếu"}, "assetPercent": 87.41},
                                                 {"assetType": {"code": "CASH", "name": "Tiền và tương đương tiền"}, "assetPercent": 11.57}],
                     "productIndustriesHoldingList": [{"industry": "Ngân hàng", "assetPercent": 34.59}]}}


def test_every_fund_s_published_holdings_are_kept_with_their_month(tmp_path):
    calls = []

    def get(url):
        calls.append(url)
        return json.dumps(detail("DCDS" if url.endswith("/28") else "VFF"))
    out = fund_holdings_sync(FundHoldingsStore(tmp_path), post=lambda u, b: listing((28, "DCDS", "10/2026"), (31, "VFF", "10/2026")), get=get,
                             now=NOW, sleep=lambda s: None)
    assert out == {"status": "ok", "fetched": 2, "unchanged": 0, "errors": {}}
    assert calls == ["https://api.fmarket.vn/res/products/28", "https://api.fmarket.vn/res/products/31"]  # every fund, not only the owner's
    dcds = fund_holdings(tmp_path)["DCDS"]
    assert dcds["as_of"] == "2026-10"
    assert dcds["stocks"] == [{"symbol": "VIC", "percent": "11.75", "industry": "Bất động sản"}, {"symbol": "TCB", "percent": "6.98", "industry": "Ngân hàng"}]
    assert dcds["bonds"] == [{"code": "VHM12612", "percent": "12.41", "industry": "Bất động sản"}]
    assert dcds["assets"] == [{"kind": "STOCK", "name": "Cổ phiếu", "percent": "87.41"}, {"kind": "CASH", "name": "Tiền và tương đương tiền", "percent": "11.57"}]


def test_a_fund_whose_month_has_not_changed_is_not_fetched_again_and_one_failing_keeps_the_rest(tmp_path):
    store = FundHoldingsStore(tmp_path)
    fund_holdings_sync(store, post=lambda u, b: listing((28, "DCDS", "10/2026")), get=lambda u: json.dumps(detail("DCDS")), now=NOW, sleep=lambda s: None)
    calls = []

    def get(url):
        calls.append(url)
        raise OSError("down")
    out = fund_holdings_sync(store, post=lambda u, b: listing((28, "DCDS", "10/2026"), (31, "VFF", "11/2026")), get=get, now=NOW, sleep=lambda s: None)
    assert calls == ["https://api.fmarket.vn/res/products/31"] and out["unchanged"] == 1 and out["errors"] == {"VFF": "OSError"}
    assert set(fund_holdings(tmp_path)) == {"DCDS"}
