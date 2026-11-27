import json
from datetime import date

from investment_agent.brief.proprietary import summarise_proprietary
from investment_agent.market.providers.vndirect_data import proprietary_trading

D = date(2026, 11, 26)
SESSIONS = [date(2026, 11, 20), date(2026, 11, 23), date(2026, 11, 24), date(2026, 11, 25), D]


def row(code, day, buy_val, sell_val, buy_vol=100, sell_vol=40, kind="STOCK"):
    return {"code": code, "type": kind, "floor": "HOSE", "date": day, "buyingVol": float(buy_vol), "sellingVol": float(sell_vol),
            "buyingVal": float(buy_val), "sellingVal": float(sell_val), "netVal": float(buy_val - sell_val),
            "netVol": float(buy_vol - sell_vol)}


INDEX = row("VNINDEX", "2026-11-23", 874_616_495_000, 517_105_285_000, 28_844_394, 23_202_400, kind="INDEX")
STOCKS = [row("FPT", "2026-11-23", 500_000_000_000, 100_000_000_000), row("HPG", "2026-11-23", 300_000_000_000, 10_000_000_000),
          row("VHM", "2026-11-23", 50_000_000_000, 300_000_000_000), row("SSI", "2026-11-23", 24_616_495_000, 107_105_285_000),
          row("ACB", "2026-11-23", 0, 0)]


def test_totals_come_from_the_vnindex_row_with_the_session_and_how_far_behind_it_is():
    s = summarise_proprietary(INDEX, STOCKS, session_date=D, sessions=SESSIONS)
    assert s["status"] == "ok" and s["date"] == "2026-11-23" and s["lag_sessions"] == 3
    assert s["buy_value_bn"] == "874.62" and s["sell_value_bn"] == "517.11" and s["net_value_bn"] == "357.51"
    assert s["buy_volume"] == 28_844_394 and s["sell_volume"] == 23_202_400
    assert s["top_buy"] == [{"symbol": "FPT", "net_value_bn": "400.00"}, {"symbol": "HPG", "net_value_bn": "290.00"}]
    assert s["top_sell"] == [{"symbol": "VHM", "net_value_bn": "-250.00"}, {"symbol": "SSI", "net_value_bn": "-82.49"}]


def test_the_session_itself_has_no_lag():
    today = row("VNINDEX", "2026-11-26", 10_000_000_000, 4_000_000_000, kind="INDEX")
    s = summarise_proprietary(today, [row("FPT", "2026-11-26", 10_000_000_000, 4_000_000_000)], session_date=D, sessions=SESSIONS)
    assert s["date"] == "2026-11-26" and s["lag_sessions"] == 0


def test_tickers_that_do_not_add_up_to_the_index_row_give_no_top_lists():
    s = summarise_proprietary(INDEX, STOCKS[:2], session_date=D, sessions=SESSIONS)
    assert s["status"] == "ok" and s["net_value_bn"] == "357.51"
    assert s["top_buy"] is None and s["top_sell"] is None
    assert s["top_reason"] == "Tổng các mã không khớp dòng tổng VN-Index của VNDirect"


def test_rows_of_another_session_are_never_counted():
    other = [*STOCKS, row("MWG", "2026-11-20", 999_000_000_000, 0)]
    assert summarise_proprietary(INDEX, other, session_date=D, sessions=SESSIONS)["top_buy"][0]["symbol"] == "FPT"


def test_no_row_or_a_row_older_than_the_sessions_kept_is_missing():
    assert summarise_proprietary(None, [], session_date=D, sessions=SESSIONS) == {
        "status": "missing", "reason": "VNDirect chưa có số tự doanh"}
    old = row("VNINDEX", "2026-11-19", 1, 0, kind="INDEX")
    assert summarise_proprietary(old, [], session_date=D, sessions=SESSIONS) == {
        "status": "missing", "reason": "Số tự doanh gần nhất của VNDirect là phiên 19/11/2026, quá cũ"}


def test_the_provider_reads_the_latest_vnindex_row_up_to_the_session_then_that_day_s_tickers():
    asked = []

    def get(url):
        asked.append(url)
        if "code:VNINDEX" in url:
            return json.dumps({"data": [INDEX]})
        return json.dumps({"data": STOCKS})
    got = proprietary_trading(D, get)
    assert got == {"index": INDEX, "stocks": STOCKS}
    assert "date:lte:2026-11-26" in asked[0] and "sort=date:desc" in asked[0]
    assert "type:STOCK~floor:HOSE~date:2026-11-23" in asked[1]


def test_the_provider_without_a_vnindex_row_asks_nothing_more():
    asked = []

    def get(url):
        asked.append(url)
        return json.dumps({"data": []})
    assert proprietary_trading(D, get) == {"index": None, "stocks": []}
    assert len(asked) == 1
