import json
from datetime import datetime

from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.series import SeriesStore
from investment_agent.market.statements import StatementStore
from investment_agent.services.cash_rank import CASH_RICH, cash_ranking

B = 10**9


def q(**values) -> dict:
    return {k: str(v * B) for k, v in values.items()}


def data(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("AAA\nBBB\nCCC\nDDD\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-11-11", "source": "t", "level": 2, "sectors": {
        "AAA": "Công nghệ Thông tin", "BBB": "Bán lẻ", "CCC": "Bất động sản", "DDD": "Hóa chất", "VCB": "Ngân hàng"}}), encoding="utf-8")
    st, fu, se = StatementStore(tmp_path / "statements"), FundamentalsStore(tmp_path / "fundamentals"), SeriesStore(tmp_path / "trend-sources")
    rows = {"AAA": (q(cash=300, st_investments=200, st_debt=100, lt_debt=0), "100000000", "20"),   # net cash 400; cap 2,000: 20%
            "BBB": (q(cash=50, st_investments=50, st_debt=200, lt_debt=100), "10000000", "50"),    # net debt 200; cap 500
            "CCC": (q(cash=100, st_investments=0, st_debt=0, lt_debt=0), None, "10"),              # no shares: no cap
            "DDD": (q(cash=10, st_debt=5, lt_debt=0), "1000000", "10")}                            # short-term investments missing
    for s, (quarter, shares, close) in rows.items():
        st.save({"symbol": s, "quarters": {"2026-Q2": q(cash=1, st_investments=1, st_debt=1, lt_debt=1), "2026-Q3": quarter}, "years": {}})
        fu.save({"symbol": s, "shares_outstanding": shares})
        se.upsert(f"{s}-1d", [(datetime(2026, 11, 13), close)])  # thousand đồng
    return tmp_path


def test_watched_non_financial_tickers_are_ranked_by_net_cash_against_market_value(tmp_path):
    rows = cash_ranking(data(tmp_path))
    assert [r["symbol"] for r in rows] == ["AAA", "BBB", "CCC", "DDD"]  # banks are left out; tickers without the ratio last
    aaa, bbb, ccc, ddd = rows
    assert aaa == {"symbol": "AAA", "sector": "Công nghệ Thông tin", "quarter": "2026-Q3", "cash_like": str(500 * B), "debt": str(100 * B),
                   "net_cash": str(400 * B), "close": "20000", "close_date": "2026-11-13", "market_cap": str(2000 * B),
                   "net_cash_to_cap": "0.2000", "missing": None}
    assert (bbb["net_cash"], bbb["net_cash_to_cap"]) == (str(-200 * B), "-0.4000")
    assert (ccc["net_cash"], ccc["market_cap"], ccc["missing"]) == (str(100 * B), None, "shares")
    assert (ddd["net_cash"], ddd["missing"]) == (None, "statements")


def test_cash_rich_are_those_whose_net_cash_is_at_least_a_fifth_of_their_market_value(tmp_path):
    rows = cash_ranking(data(tmp_path))
    assert CASH_RICH == __import__("decimal").Decimal("0.20")
    assert [r["symbol"] for r in rows if r["net_cash_to_cap"] is not None and float(r["net_cash_to_cap"]) >= 0.2] == ["AAA"]
