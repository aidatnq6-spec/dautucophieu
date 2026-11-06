import json
from datetime import datetime, timezone

from investment_agent.market.fund_nav import FundNavStore, fund_nav_sync, fund_navs

NOW = datetime(2026, 11, 6, 13, 0, tzinfo=timezone.utc)


def page(*rows):
    return {"status": 200, "data": {"total": len(rows), "rows": list(rows)}}


def row(code, nav, ms, name="Quỹ"):
    return {"id": 1, "shortName": code, "code": code, "name": name, "nav": nav, "status": "PRODUCT_ACTIVE", "extra": {"lastNAVDate": ms}}


def test_one_call_stores_every_fund_with_its_valuation_date(tmp_path):
    calls = []
    out = fund_nav_sync(FundNavStore(tmp_path), post=lambda url, body: calls.append((url, body)) or page(
        row("VFF", 27214.48, 1793811600000, "Quỹ trái phiếu A"), row("DCBF", 30863.88, 1793725200000), row("XYZ", None, 1793811600000)), now=NOW)
    assert out == {"status": "ok", "funds": 2}
    assert len(calls) == 1 and calls[0][0] == "https://api.fmarket.vn/res/products/filter"
    assert "VFF" not in json.dumps(calls[0][1])  # nothing about the owner's funds is sent
    assert fund_navs(tmp_path) == {"VFF": {"name": "Quỹ trái phiếu A", "nav": "27214.48", "date": "2026-11-05"},
                                   "DCBF": {"name": "Quỹ", "nav": "30863.88", "date": "2026-11-04"}}
    stored = json.loads((tmp_path / "fund-nav.json").read_text(encoding="utf-8"))
    assert stored["source"] == "Fmarket" and stored["fetched_at"] == "2026-11-06T13:00:00+00:00"


def test_a_failed_or_empty_answer_keeps_what_was_stored_and_a_fund_that_drops_out_keeps_its_old_nav(tmp_path):
    store = FundNavStore(tmp_path)
    fund_nav_sync(store, post=lambda u, b: page(row("VFF", 27214.48, 1793811600000), row("DCBF", 30863.88, 1793725200000)), now=NOW)
    assert fund_nav_sync(store, post=lambda u, b: page(), now=NOW)["status"] == "error"

    def boom(u, b):
        raise OSError("down")
    assert fund_nav_sync(store, post=boom, now=NOW)["status"] == "error"
    assert set(fund_navs(tmp_path)) == {"VFF", "DCBF"}
    fund_nav_sync(store, post=lambda u, b: page(row("VFF", 27300, 1793898000000)), now=NOW)
    assert fund_navs(tmp_path)["VFF"] == {"name": "Quỹ", "nav": "27300", "date": "2026-11-06"}
    assert fund_navs(tmp_path)["DCBF"]["date"] == "2026-11-04"


def test_no_data_dir_or_no_file_means_no_nav(tmp_path):
    assert fund_navs(None) == {} and fund_navs(tmp_path) == {}
