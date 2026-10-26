from datetime import date, datetime
from decimal import Decimal

from investment_agent.valuation.reference import (
    Settings, metrics, methods_for, reference_board, value_ticker, year_end_prices,
)

TODAY = date(2026, 10, 26)
PRICES = {2021: Decimal(15000), 2022: Decimal(14400), 2023: Decimal(10000), 2024: Decimal(21000), 2025: Decimal(26000)}


def record(issues=()):
    years = {"2021": ("1000000000", "1000", "10000000000"), "2022": ("1200000000", "1200", "11000000000"),
             "2023": ("1000000000", "1000", "12000000000"), "2024": ("1500000000", "1500", "13000000000"),
             "2025": ("2000000000", "2000", "15000000000")}
    quarters = {q: {"npat": "550000000"} for q in ("2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2")}
    quarters["2025-Q2"] = {"npat": "500000000", "equity": "14000000000"}
    quarters["2026-Q2"]["equity"] = "16000000000"
    divs = [{"date": f"{y}-07-01", "cash": "1000"} for y in (2021, 2022, 2023, 2024)] + [
        {"date": "2025-12-01", "cash": "1000"}, {"date": "2026-05-28", "cash": "1000"}]
    return {"symbol": "AAA", "fetched_at": "2026-10-26T00:00:00+00:00", "source": "t",
            "years": {y: {"npat": n, "eps": e, "equity": q} for y, (n, e, q) in years.items()},
            "quarters": dict(sorted(quarters.items())), "dividends": divs, "issues": list(issues)}


def test_metrics_derive_shares_ttm_eps_bvps_roe_and_history():
    m = metrics(record(), today=TODAY, year_end_prices=PRICES)
    assert (m["shares"], m["eps_ttm"], m["bvps"]) == (Decimal(1000000), Decimal(2200), Decimal(16000))
    assert m["roe"].quantize(Decimal("0.0001")) == Decimal("0.1467")
    assert m["pe_history"] == {2021: 15, 2022: 12, 2023: 10, 2024: 14, 2025: 13}
    assert m["pb_history"][2021] == Decimal("1.5") and m["dividend_ttm"] == Decimal(2000) and m["paying_years"] == 5
    assert m["latest_year"] == "2025" and m["latest_quarter"] == "2026-Q2"


def test_share_issues_after_the_annual_report_raise_the_share_count():
    m = metrics(record([{"date": "2026-09-21", "ratio": "0.1"}, {"date": "2025-07-01", "ratio": "0.5"}]), today=TODAY, year_end_prices=PRICES)
    assert m["shares"] == Decimal(1100000)  # only the 2026 issue is after FY2025


def test_each_method_on_the_hand_computed_case():
    m = metrics(record(), today=TODAY, year_end_prices=PRICES)
    peers = {"pe": [Decimal(10), Decimal(12), Decimal(14)], "pb": [Decimal(1), Decimal(2), Decimal(3)]}
    got = {x["method"]: x["value"] for x in methods_for(["pe_history", "pb_history", "pe_peers", "pb_peers", "justified_pb", "ddm", "pe_normalized"],
                                                        m, peers, Settings())}
    assert got == {"pe_history": Decimal(28600), "pb_history": Decimal(24000), "pe_peers": Decimal(26400), "pb_peers": Decimal(32000),
                   "justified_pb": Decimal(19333), "ddm": Decimal(26250), "pe_normalized": Decimal(17420)}


def test_methods_explain_why_they_do_not_apply():
    m = metrics(record(), today=TODAY, year_end_prices={2025: Decimal(26000)})
    out = {x["method"]: x for x in methods_for(["pe_history", "pe_peers", "justified_pb"], m, {"pe": [Decimal(10)], "pb": []},
                                               Settings(required_return=Decimal("0.13"), long_term_growth=Decimal("0.20")))}
    assert out["pe_history"]["value"] is None and "4 năm" in out["pe_history"]["reason"]
    assert out["pe_peers"]["value"] is None and "3 mã" in out["pe_peers"]["reason"]
    assert out["justified_pb"]["value"] is None


def test_verdict_uses_the_median_of_sector_methods_and_the_threshold():
    m = metrics(record(), today=TODAY, year_end_prices=PRICES)
    peers = {"pe": [Decimal(10), Decimal(12), Decimal(14)], "pb": [Decimal(1), Decimal(2), Decimal(3)]}
    tech = lambda price: value_ticker("AAA", "Công nghệ Thông tin", m, price, peers, Settings())  # noqa: E731
    assert tech(Decimal(20000))["fair"] == "26400" and tech(Decimal(20000))["verdict"] == "cheap"
    assert tech(Decimal(30000))["verdict"] == "fair" and tech(Decimal(32000))["verdict"] == "expensive"
    bank = value_ticker("AAA", "Ngân hàng", m, Decimal(26300), peers, Settings())
    assert (bank["fair"], bank["low"], bank["high"], bank["verdict"]) == ("26300", "19333", "32000", "fair")
    lonely = value_ticker("AAA", "Bất động sản", metrics(record(), today=TODAY, year_end_prices={}), Decimal(1), peers, Settings())
    assert lonely["verdict"] == "insufficient" and lonely["fair"] is None
    assert value_ticker("AAA", "Ngân hàng", m, None, peers, Settings())["verdict"] == "insufficient"


def test_year_end_prices_take_the_last_close_of_each_finished_year_in_dong():
    pts = [(datetime(2024, 12, 30), 20.5), (datetime(2024, 12, 31), 21.0), (datetime(2025, 12, 31), 26.0), (datetime(2026, 10, 23), 57.0)]
    assert year_end_prices(pts, today=TODAY) == {2024: Decimal("21000"), 2025: Decimal("26000")}


def test_board_values_every_symbol_with_peers_from_the_same_sector():
    recs = {s: record() for s in ("AAA", "BBB", "CCC", "DDD")}
    board = reference_board(["AAA", "BBB", "CCC", "DDD", "EEE"], sectors={s: "Ngân hàng" for s in recs},
                            records=recs, prices={s: Decimal(26000) for s in recs}, year_end={s: PRICES for s in recs},
                            settings=Settings(), today=TODAY, held={"AAA"})
    rows = {r["symbol"]: r for r in board["rows"]}
    assert rows["AAA"]["held"] is True and rows["AAA"]["verdict"] in {"cheap", "fair", "expensive"}
    assert rows["EEE"]["verdict"] == "insufficient" and rows["EEE"]["sector"] == "Chưa phân ngành"
    assert board["settings"] == {"required_return": "0.13", "long_term_growth": "0.05", "threshold": "0.2"}


def test_listed_shares_stand_in_when_eps_is_not_reported():
    r = record()
    for y in r["years"].values():
        del y["eps"]
    r["shares_outstanding"] = "1000000"
    m = metrics(r, today=TODAY, year_end_prices=PRICES)
    assert m is not None and m["shares"] == Decimal(1000000) and m["eps_ttm"] == Decimal(2200)
