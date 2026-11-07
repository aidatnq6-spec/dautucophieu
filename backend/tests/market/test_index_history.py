import json
from datetime import date, datetime, timezone
from decimal import Decimal

from investment_agent.market.index_history import IndexHistoryStore, build_history, compare, compute_index, parse_closes, parse_quarters

B = 10**9


def statements(symbol, *rows):
    return json.dumps({"data": [{"code": symbol, "itemCode": float(item), "reportType": "QUARTER", "modelType": 1.0, "numericValue": v, "fiscalDate": f,
                                 "createdDate": "2019-12-01 00:00:00"} for item, v, f in rows]})


def test_quarters_take_parent_profit_parent_equity_and_shares_whatever_the_industry_layout():
    text = statements("VCB", (23000, 5e12, "2016-12-31"), (14000, 50e12, "2016-12-31"), (14240, 1e12, "2016-12-31"), (14110, 35e12, "2016-12-31"),
                      (23000, 4e12, "2016-09-30"), (14000, 1, "2016-09-30"), (14000, 2, "2016-09-30"), (23000, 1, "2016-06-30"))
    q = parse_quarters(text, symbol="VCB")
    assert q["2016-Q4"] == {"npat_parent": Decimal(5e12), "equity_parent": Decimal(49e12), "shares": Decimal("3.5e9")}
    assert q["2016-Q3"] == {"npat_parent": Decimal(4e12)}  # two equity figures: none kept
    assert q["2016-Q2"] == {"npat_parent": Decimal(1)}


def test_closes_keep_every_day_before_2018_and_each_month_s_last_after():
    text = json.dumps({"data": [{"code": "AAA", "date": d, "close": c} for d, c in
                                (("2017-12-28", 10), ("2017-12-29", 11), ("2018-01-30", 12), ("2018-01-31", 13), ("2018-02-28", 14), ("2018-02-27", 0))]})
    assert parse_closes(text, symbol="AAA") == [(date(2017, 12, 28), Decimal(10)), (date(2017, 12, 29), Decimal(11)), (date(2018, 1, 31), Decimal(13)),
                                                (date(2018, 2, 28), Decimal(14))]


def record(quarters, closes):
    return {"quarters": {q: {k: str(v) for k, v in f.items()} for q, f in quarters.items()}, "closes": [[d.isoformat(), str(c)] for d, c in closes]}


def test_the_index_is_total_capitalisation_over_total_parent_profit_and_equity_of_the_tickers_with_everything_out():
    full = {f"2015-Q{k}": {"npat_parent": 1 * B, "equity_parent": 20 * B, "shares": 10**8} for k in (1, 2, 3, 4)}
    a = record(full, [(date(2016, 3, 1), Decimal(10))])  # 2015-Q4 is out from 14/02/2016: 1,000 tỷ cap, 4 tỷ profit, 20 tỷ equity
    b = record({**full, "2015-Q4": {"npat_parent": 3 * B, "equity_parent": 40 * B, "shares": 10**8}}, [(date(2016, 3, 1), Decimal(30))])  # 3,000 tỷ, 6 tỷ, 40 tỷ
    c = record({"2015-Q4": {"npat_parent": 1 * B, "equity_parent": 10 * B, "shares": 10**8}}, [(date(2016, 3, 1), Decimal(5))])  # no four quarters: left out
    out = compute_index({"A": a, "B": b, "C": c}, before=date(2018, 1, 1))
    assert out[date(2016, 3, 1)] == {"pe": Decimal("400"), "pb": Decimal("66.67"), "tickers": 2}  # 4,000 / 10 ; 4,000 / 60


def test_a_quarter_counts_only_once_out_and_the_share_count_follows_the_latest_out():
    q = {f"2015-Q{k}": {"npat_parent": 1 * B, "equity_parent": 20 * B, "shares": 10**8} for k in (1, 2, 3, 4)}
    q["2016-Q1"] = {"npat_parent": 1 * B, "equity_parent": 20 * B, "shares": 2 * 10**8}
    a = record(q, [(date(2016, 5, 10), Decimal(10)), (date(2016, 5, 20), Decimal(10))])
    out = compute_index({"A": a}, before=date(2018, 1, 1))
    assert out[date(2016, 5, 10)]["pe"] == Decimal("250") and out[date(2016, 5, 20)]["pe"] == Decimal("500")  # 2016-Q1 out from 15/05: twice the shares


def test_comparison_with_vndirect_over_the_months_both_have():
    calc = {date(2018, 1, 31): {"pe": Decimal("20"), "pb": Decimal("3"), "tickers": 300}, date(2018, 2, 28): {"pe": Decimal("15"), "pb": Decimal("2"), "tickers": 300}}
    vnd = {"pe": [(datetime(2018, 1, 31), 18.0), (datetime(2018, 2, 28), 15.0)], "pb": [(datetime(2018, 1, 31), 3.0)]}
    out = compare(calc, vnd)
    assert out["pe"] == {"months": 2, "mean_abs": "0.0556", "max_abs": "0.1111", "from": "2018-01", "to": "2018-02"}
    assert out["pb"]["months"] == 1 and out["pb"]["mean_abs"] == "0.0000"


def test_build_fetches_each_ticker_once_and_resumes(tmp_path):
    store, urls = IndexHistoryStore(tmp_path), []

    def get(url):
        urls.append(url)
        sym = url.split("code:")[1].split("~")[0].split("&")[0]
        if "stock_prices" in url:
            return json.dumps({"data": [{"code": sym, "date": "2016-03-01", "close": 10}]})
        return statements(sym, (23000, 1e9, "2015-12-31"))
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    assert build_history(store, ["AAA", "BBB"], get=get, now=now, sleep=lambda s: None) == {"AAA": "ok", "BBB": "ok"}
    assert len(urls) == 4 and store.read("AAA")["quarters"]["2015-Q4"]["npat_parent"] == "1000000000"
    assert build_history(store, ["AAA", "BBB", "CCC"], get=get, now=now, sleep=lambda s: None) == {"CCC": "ok"} and len(urls) == 6


def test_cli_builds_works_out_compares_and_keeps_the_part_before_vndirect(tmp_path, capsys):
    from investment_agent.cli import index_history_cli
    from investment_agent.market.series import SeriesStore
    (tmp_path / "hose-listing.json").write_text(json.dumps({"at": "2026-11-07T00:00:00+00:00", "listing": {"symbols": ["AAA"], "icb_codes": {}}}),
                                                encoding="utf-8")
    SeriesStore(tmp_path / "index-valuation").upsert("VNINDEX-pe-1d", [(datetime(2017, 12, 15), "18"), (datetime(2018, 1, 31), "20")])

    def get(url):
        if "stock_prices" in url:
            return json.dumps({"data": [{"code": "AAA", "date": d, "close": 10} for d in ("2016-03-01", "2017-12-14", "2018-01-31")]})
        ends = [f"{y}-{md}" for y in (2015, 2016, 2017) for md in ("03-31", "06-30", "09-30", "12-31")]
        return statements("AAA", *[(23000, 1e9, f) for f in ends], *[(14000, 20e9, f) for f in ends], *[(14110, 1e12, f) for f in ends])
    assert index_history_cli(tmp_path, get=get, now=datetime(2026, 11, 7, tzinfo=timezone.utc), sleep=lambda s: None) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["built"] == {"AAA": "ok"} and out["compare"]["pe"]["months"] == 2  # 2017-12 and 2018-01 are on both sides
    kept = SeriesStore(tmp_path / "index-valuation").read("VNINDEX-pe-calc-1d")
    assert [t.date() for t, _ in kept] == [date(2016, 3, 1), date(2017, 12, 14)]  # only the days before VNDirect's first
    assert out["vn30"]["basket"] == "top30" and out["compare"]["basket"] == "all"
    assert SeriesStore(tmp_path / "index-valuation").read("VN30-pe-calc-1d")  # one ticker is the largest thirty here
    assert json.loads((tmp_path / "index-valuation" / "VN30-calc-check.json").read_text(encoding="utf-8"))["basket"] == "top30"


def test_a_ticker_missing_the_quarter_due_is_left_out_not_valued_on_older_figures():
    full = {f"2015-Q{k}": {"npat_parent": 1 * B, "equity_parent": 20 * B, "shares": 10**8} for k in (1, 2, 3, 4)}
    a = record(full, [(date(2016, 3, 1), Decimal(10)), (date(2016, 6, 1), Decimal(10))])  # 2016-Q1 is due from 15/05/2016 and absent
    out = compute_index({"A": a})
    assert date(2016, 3, 1) in out and date(2016, 6, 1) not in out


def test_a_basket_of_the_largest_by_capitalisation_holds_from_february_and_august():
    from investment_agent.market.index_history import top_members
    full = {f"{y}-Q{k}": {"npat_parent": 1 * B, "equity_parent": 20 * B, "shares": 10**8} for y in (2015, 2016) for k in (1, 2, 3, 4)}
    big = record(full, [(date(2015, 12, 31), Decimal(50)), (date(2016, 6, 30), Decimal(5))])
    small = record(full, [(date(2015, 12, 31), Decimal(10)), (date(2016, 6, 30), Decimal(40))])
    member = top_members({"BIG": big, "SMALL": small}, size=1)
    assert member("BIG", date(2016, 3, 1)) and not member("SMALL", date(2016, 3, 1))  # chosen on 31/12/2015, from 01/02/2016
    assert member("SMALL", date(2016, 8, 10)) and not member("BIG", date(2016, 8, 10))  # chosen on 30/06/2016, from 01/08/2016
    assert member("BIG", date(2016, 7, 20))  # until 31 July the January choice stands


def test_the_index_can_be_limited_to_a_basket():
    full = {f"2015-Q{k}": {"npat_parent": 1 * B, "equity_parent": 20 * B, "shares": 10**8} for k in (1, 2, 3, 4)}
    a = record(full, [(date(2016, 3, 1), Decimal(10))])
    b = record(full, [(date(2016, 3, 1), Decimal(30))])
    out = compute_index({"A": a, "B": b}, members=lambda s, d: s == "B")
    assert out[date(2016, 3, 1)] == {"pe": Decimal("750"), "pb": Decimal("150"), "tickers": 1}  # 3,000 tỷ / 4 tỷ ; / 20 tỷ
