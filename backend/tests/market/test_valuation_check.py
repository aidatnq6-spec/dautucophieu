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


def rows_of(*codes, total=None, profit=False):
    data = [{"code": c, "ratioCode": "NET_PROFIT_TR", "reportDate": "2026-09-30", "value": 1e11} for c in codes] if profit else \
        [{"code": c, "ratioCode": "MARKETCAP", "reportDate": "2026-11-06", "value": 1e12} for c in codes]
    return json.dumps({"data": data, "totalElements": total if total is not None else len(data)})


def test_the_watched_tickers_are_read_in_one_call_per_batch_not_two_each(tmp_path):
    """55 tickers took about 110 calls and 48 s; one call per batch of 50 for each kind gives the same figures (checked live 21/11/2026)."""
    store, calls = ValuationCheckStore(tmp_path), []

    def get(url):
        calls.append(url)
        return rows_of("AAA", "BBB", profit="NET_PROFIT_TR" in url)
    assert fetch_checks(store, ["AAA", "BBB"], get=get, today=TODAY, sleep=lambda s: None) == {"AAA": "ok", "BBB": "ok"}
    assert len(calls) == 2 and "code:AAA,BBB" in calls[0]
    assert store.read("BBB")["market_cap"] == "1000000000000" and store.read("BBB")["profit_quarter"] == "2026-Q3"


def test_a_batch_cut_short_is_read_ticker_by_ticker_again(tmp_path):
    store, calls = ValuationCheckStore(tmp_path), []

    def get(url):
        calls.append(url)
        if "code:AAA,BBB" in url:
            return rows_of("AAA", total=999, profit="NET_PROFIT_TR" in url)  # VNDirect says there are more rows than it gave
        return page(("MARKETCAP", "2026-11-06", 1e12))
    assert fetch_checks(store, ["AAA", "BBB"], get=get, today=TODAY, sleep=lambda s: None) == {"AAA": "ok", "BBB": "ok"}
    assert any(u.split("code:")[1].startswith("BBB~") for u in calls)


def test_a_figure_more_than_a_tenth_away_is_flagged_and_a_missing_side_is_only_shown():
    ours = {"market_cap": "1050000000000", "pe": "15.00", "pb": None, "close_date": "2026-11-06"}
    out = compare(ours, {"date": "2026-11-06", "market_cap": "1000000000000", "pe": "12.5", "pb": "1.5"})
    rows = {r["key"]: r for r in out["rows"]}
    assert out["date"] == "2026-11-06" and rows["market_cap"]["off"] is False and rows["market_cap"]["diff"] == "0.0500"
    assert rows["pe"]["off"] is True and rows["pe"]["diff"] == "0.2000" and rows["pb"]["off"] is False and rows["pb"]["diff"] is None
    assert out["flagged"] == 1
    assert compare(ours, None) is None


def test_when_vndirect_has_not_taken_in_the_latest_quarter_its_pe_is_compared_on_the_same_four_quarters():
    ours = {"market_cap": "11133000000000", "pe": "23.39", "pb": "1.0", "close_date": "2026-11-06"}
    theirs = {"date": "2026-11-06", "market_cap": "11133000000000", "pe": "18.04", "pb": "1.0", "profit_quarter": "2026-Q2"}
    ttm = {"2026-Q2": "617100000000", "2026-Q3": "476000000000"}
    out = compare(ours, theirs, ttm=ttm)
    pe = {r["key"]: r for r in out["rows"]}["pe"]
    assert pe["off"] is False and pe["diff"] == "0.0000" and out["flagged"] == 0
    assert "Q2/2026" in pe["note"] and "Q3/2026" in pe["note"] and "18,04x" in pe["note"]


def test_a_real_gap_on_the_same_four_quarters_is_still_flagged_and_an_up_to_date_source_is_compared_as_it_stands():
    ours = {"market_cap": "1000", "pe": "20", "pb": "1", "close_date": "2026-11-06"}
    behind = compare(ours, {"date": "d", "market_cap": "1000", "pe": "10", "pb": "1", "profit_quarter": "2026-Q2"}, ttm={"2026-Q2": "50", "2026-Q3": "50"})
    assert {r["key"]: r for r in behind["rows"]}["pe"]["off"] is True  # 1000 / 50 = 20x on their own quarters, against 10x
    level = compare(ours, {"date": "d", "market_cap": "1000", "pe": "20", "pb": "1", "profit_quarter": "2026-Q3"}, ttm={"2026-Q2": "50", "2026-Q3": "50"})
    assert {r["key"]: r for r in level["rows"]}["pe"]["note"] is None


def test_the_quarter_vndirects_profit_runs_to_is_read_with_the_figures(tmp_path):
    store = ValuationCheckStore(tmp_path)

    def get(url):
        if "NET_PROFIT_TR" in url:
            return json.dumps({"data": [{"ratioCode": "NET_PROFIT_TR", "reportDate": "2026-06-30", "value": 6e11}, {"ratioCode": "NET_PROFIT_TR", "reportDate": "2026-03-31", "value": 5e11}]})
        return page(("MARKETCAP", "2026-11-06", 1e12))
    assert fetch_checks(store, ["AAA"], get=get, today=TODAY, sleep=lambda s: None) == {"AAA": "ok"}
    assert store.read("AAA")["profit_quarter"] == "2026-Q2"

