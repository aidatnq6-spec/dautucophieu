import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from investment_agent.brief.snapshot import BriefStore, build_snapshot, latest_session
from investment_agent.market.calendar import TradingCalendar
from investment_agent.market.providers.vnstock_adapter import flatten_board

VN = ZoneInfo("Asia/Ho_Chi_Minh")
D = date(2026, 10, 26)
NOW = datetime(2026, 10, 26, 15, 40, tzinfo=VN)
CAL = TradingCalendar(version="t", source="synthetic", holidays=frozenset(), first=date(2026, 1, 1), last=date(2026, 12, 31))
BOARD = [{"symbol": "FPT", "trading_date": "2026-10-26", "ref_price": 57000, "match_price": 56000, "accumulated_value": 572175.08,
          "accumulated_volume": 10104800, "foreign_buy_volume": 1, "foreign_sell_volume": 2, "foreign_buy_value": 1_000_000_000,
          "foreign_sell_value": 3_000_000_000, "icb_code2": "9500"}]
RSS = ('<rss><item><title>FPT ký hợp đồng</title><link>https://cafef.vn/a.chn</link>'
       '<pubDate>Mon, 26 Oct 2026 10:00:00 +0700</pubDate></item></rss>')
HOSE_EMPTY = json.dumps({"data": [], "success": True})


def deps(tmp_path, **over):
    base = dict(session_date=D, previous_session=date(2026, 10, 23), now=NOW,
                listing=lambda: {"symbols": ["FPT"], "icb_names": {"9500": "Công nghệ Thông tin"}},
                board=lambda symbols: BOARD,
                series=lambda index_id: [(datetime(2026, 10, 23), 1658.52), (datetime(2026, 10, 26), 1650.12)],
                hose_get=lambda url: HOSE_EMPTY, rss_get=lambda url: RSS, store=BriefStore(tmp_path))
    return {**base, **over}


def test_all_sections_are_built_and_stored(tmp_path):
    snap = build_snapshot(**deps(tmp_path))
    assert snap["session_date"] == "2026-10-26"
    assert snap["indices"]["rows"][0]["change"] == "-8.40"
    assert snap["board"]["breadth"]["down"] == 1 and snap["board"]["sectors"][0]["sector"] == "Công nghệ Thông tin"
    assert snap["hose"] == {"status": "missing", "reason": "HOSE chưa công bố"}
    assert snap["proprietary"] == {"status": "missing", "reason": "Chưa có nguồn miễn phí"}
    assert snap["news"]["status"] == "ok" and snap["news"]["items"][0]["url"] == "https://cafef.vn/a.chn"
    assert len(snap["news"]["items"]) == 1  # five feeds served the same item; deduplicated
    assert BriefStore(tmp_path).read(D) == snap


def test_each_failing_source_only_blanks_its_own_section(tmp_path):
    def boom(*a):
        raise OSError("down")
    snap = build_snapshot(**deps(tmp_path, board=boom, rss_get=boom))
    assert snap["board"]["status"] == "missing" and snap["news"]["status"] == "missing"
    assert snap["indices"]["status"] == "ok"


def test_a_later_failure_never_erases_an_earlier_good_section(tmp_path):
    build_snapshot(**deps(tmp_path))
    def boom(*a):
        raise OSError("down")
    again = build_snapshot(**deps(tmp_path, board=boom, now=datetime(2026, 10, 27, 7, 0, tzinfo=VN)))
    assert again["board"]["status"] == "ok" and again["board"]["breadth"]["down"] == 1


def test_board_of_the_next_session_is_not_used_for_this_one(tmp_path):
    later = [{**BOARD[0], "trading_date": "2026-10-27"}]
    snap = build_snapshot(**deps(tmp_path, board=lambda s: later))
    assert snap["board"] == {"status": "missing", "reason": "Bảng giá chưa phải phiên này"}


def test_latest_session_switches_at_three_pm_and_skips_weekends():
    assert latest_session(datetime(2026, 10, 26, 14, 59, tzinfo=VN), CAL) == date(2026, 10, 23)
    assert latest_session(datetime(2026, 10, 26, 15, 0, tzinfo=VN), CAL) == date(2026, 10, 26)
    assert latest_session(datetime(2026, 10, 25, 9, 0, tzinfo=VN), CAL) == date(2026, 10, 23)


def test_price_board_columns_are_flattened():
    cols = pd.MultiIndex.from_tuples([("listing", "symbol"), ("listing", "trading_date"), ("listing", "ref_price"), ("listing", "icb_code2"),
                                      ("match", "match_price"), ("match", "accumulated_value"), ("match", "accumulated_volume"),
                                      ("match", "foreign_buy_volume"), ("match", "foreign_sell_volume"), ("match", "foreign_buy_value"),
                                      ("match", "foreign_sell_value"), ("bid_ask", "bid_1_price")])
    frame = pd.DataFrame([["FPT", "2026-10-26", 57000, "9500", 56000, 572175.08, 10104800, 1, 2, 3, 4, 55900]], columns=cols)
    assert flatten_board(frame) == [{"symbol": "FPT", "trading_date": "2026-10-26", "ref_price": 57000, "icb_code2": "9500",
                                     "match_price": 56000, "accumulated_value": 572175.08, "accumulated_volume": 10104800,
                                     "foreign_buy_volume": 1, "foreign_sell_volume": 2, "foreign_buy_value": 3, "foreign_sell_value": 4}]


def test_sector_codes_come_from_the_listing_when_the_board_has_none(tmp_path):
    board = [{**BOARD[0], "icb_code2": None}]
    listing = lambda: {"symbols": ["FPT"], "icb_names": {"9500": "Công nghệ Thông tin"}, "icb_codes": {"FPT": "9500"}}
    snap = build_snapshot(**deps(tmp_path, board=lambda s: board, listing=listing))
    assert snap["board"]["sectors"][0]["sector"] == "Công nghệ Thông tin"
