import json
from datetime import date

from investment_agent.market.valuation_check import ValuationCheckStore, compare, fetch_checks, parse_latest

TODAY = date(2026, 11, 9)


def page(*rows):
    return json.dumps({"data": [{"code": "AAA", "ratioCode": c, "reportDate": d, "value": v} for c, d, v in rows]})


def test_each_figure_is_its_latest_up_to_today_and_a_later_dated_row_is_not_taken():
    got = parse_latest(page(("MARKETCAP", "2026-11-06", 1e12), ("MARKETCAP", "2026-11-05", 9e11), ("PRICE_TO_EARNINGS", "2026-12-31", 99.0), ("PRICE_TO_EARNINGS", "2026-11-06", 12.5),
                            ("PRICE_TO_BOOK", "2026-11-06", 1.5), ("OUTSTANDING_SHARES", "2026-12-31", 243900000)), today=TODAY)  # VNDirect dates today's share count at the year's end
    assert got == {"date": "2026-11-06", "market_cap": "1000000000000", "pe": "12.5", "pb": "1.5", "shares": "243900000"}


def test_only_watched_tickers_are_read_and_one_failure_does_not_stop_the_others(tmp_path):
    store = ValuationCheckStore(tmp_path)

    def get(url):
        if "code:BBB" in url:
            raise RuntimeError("down")
        return page(("MARKETCAP", "2026-11-06", 1e12))
    assert fetch_checks(store, ["AAA", "BBB"], get=get, today=TODAY, sleep=lambda s: None) == {"AAA": "ok", "BBB": "error:RuntimeError"}
    assert store.read("AAA")["market_cap"] == "1000000000000" and store.read("BBB") is None


def test_a_figure_more_than_a_tenth_away_is_flagged_and_a_missing_side_is_only_shown():
    ours = {"market_cap": "1050000000000", "pe": "15.00", "pb": None, "close_date": "2026-11-06"}
    out = compare(ours, {"date": "2026-11-06", "market_cap": "1000000000000", "pe": "12.5", "pb": "1.5"})
    rows = {r["key"]: r for r in out["rows"]}
    assert out["date"] == "2026-11-06" and rows["market_cap"]["off"] is False and rows["market_cap"]["diff"] == "0.0500"
    assert rows["pe"]["off"] is True and rows["pe"]["diff"] == "0.2000" and rows["pb"]["off"] is False and rows["pb"]["diff"] is None
    assert out["flagged"] == 1
    assert compare(ours, None) is None
