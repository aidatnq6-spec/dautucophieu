import json
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.series import SeriesStore
from investment_agent.market.view import PricePoint, SyntheticMarket
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def test_fairvalue_lists_every_watched_ticker_with_methods(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"FPT": "Công nghệ Thông tin", "VCB": "Ngân hàng"}}), encoding="utf-8")
    years = {str(y): {"npat": "1000000000", "eps": "1000", "equity": "10000000000"} for y in range(2020, 2026)}
    quarters = {q: {"npat": "250000000", "equity": "10000000000"} for q in ("2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2")}
    divs = [{"date": f"{y}-07-01", "cash": "500"} for y in range(2021, 2026)] + [{"date": "2026-07-01", "cash": "500"}]
    FundamentalsStore(tmp_path / "fundamentals").save({"symbol": "FPT", "fetched_at": "2026-10-26T00:00:00+00:00", "source": "t",
                                                      "years": years, "quarters": quarters, "dividends": divs, "issues": []})
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(y, 12, 31), "12") for y in range(2020, 2026)])
    market = SyntheticMarket(prices={"FPT": PricePoint(Decimal(9000), date(2027, 1, 14))})
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=market, data_dir=tmp_path)
    body = call(TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock, "GET", "/internal/fairvalue").json()
    rows = {r["symbol"]: r for r in body["rows"]}
    assert rows["FPT"]["fair"] is not None and rows["FPT"]["verdict"] in {"cheap", "fair", "expensive"}
    assert all(isinstance(m["value"], (str, type(None))) for m in rows["FPT"]["methods"])
    assert rows["VCB"]["verdict"] == "insufficient" and rows["VCB"]["reason"] == "Chưa có báo cáo tài chính"
    assert body["settings"]["threshold"] == "0.2"


def test_history_gives_monthly_pe_pb_for_a_watched_ticker_only(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    years = {str(y): {"npat": "1000000000", "eps": "1000", "equity": "10000000000"} for y in range(2018, 2026)}
    FundamentalsStore(tmp_path / "fundamentals").save({"symbol": "FPT", "fetched_at": "2026-10-26T00:00:00+00:00", "source": "t",
                                                      "years": years, "quarters": {}, "dividends": [], "issues": []})
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(2025, m, 28), "12") for m in range(1, 13)])
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=SyntheticMarket(prices={}), data_dir=tmp_path)
    client = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    body = call(client, clock, "GET", "/internal/fairvalue/history/FPT").json()
    assert body["symbol"] == "FPT" and len(body["pe"]["points"]) == 12 and body["pe"]["latest"] == "12.00" and body["pb"]["latest"] == "1.20"
    assert call(client, clock, "GET", "/internal/fairvalue/history/ZZZ").status_code == 404


def test_fairvalue_values_the_two_indices_from_their_stored_multiples(tmp_path):
    from datetime import timedelta
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    clock = Clock()
    today = date(2027, 1, 15)  # the signed client's clock
    days = [datetime.combine(today - timedelta(days=i), datetime.min.time()) for i in range(1, 6 * 365) if (today - timedelta(days=i)).weekday() < 5][::-1]
    store = SeriesStore(tmp_path / "index-valuation")
    store.upsert("VNINDEX-pe-1d", [(d, "15") for d in days[:-1]] + [(days[-1], "12")])
    store.upsert("VNINDEX-pb-1d", [(d, "2") for d in days])
    SeriesStore(tmp_path / "trend-sources").upsert("VNINDEX-1d", [(days[-1], "1800")])
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=SyntheticMarket(prices={}), data_dir=tmp_path)
    body = call(TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock, "GET", "/internal/fairvalue").json()
    rows = {r["symbol"]: r for r in body["indices"]}
    assert rows["VNINDEX"]["fair"] == "2025.00" and rows["VNINDEX"]["close"] == "1800.00" and rows["VNINDEX"]["verdict"] == "fair"
    assert rows["VN30"]["verdict"] == "insufficient" and {m["reason"] for m in rows["VN30"]["methods"]} == {"Chưa có số liệu"}


def test_history_of_an_index_charts_its_stored_daily_multiples(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    store = SeriesStore(tmp_path / "index-valuation")
    store.upsert("VN30-pe-1d", [(datetime(2025, m, 28), "12") for m in range(1, 13)])
    store.upsert("VN30-pb-1d", [(datetime(2025, m, 28), "2") for m in range(1, 13)])
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=SyntheticMarket(prices={}), data_dir=tmp_path)
    body = call(TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock, "GET", "/internal/fairvalue/history/VN30").json()
    assert body["symbol"] == "VN30" and body["kind"] == "index" and len(body["pe"]["points"]) == 12 and body["pb"]["latest"] == "2.00"


def test_fairvalue_rows_carry_report_quality_and_a_new_quarter_mark(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"FPT": "Công nghệ Thông tin", "VCB": "Ngân hàng"}}), encoding="utf-8")
    annual = {str(y): {"revenue": "100", "gross_profit": "30", "profit": "10", "total_assets": "100", "cfo": "12"} for y in (2024, 2025)}
    store = FundamentalsStore(tmp_path / "fundamentals")
    store.save({"symbol": "FPT", "fetched_at": "2027-01-14T00:00:00+00:00", "source": "t", "years": {}, "quarters": {}, "dividends": [], "issues": [],
                "annual": annual, "share_issues": [], "latest_quarter_seen": {"quarter": "2026-Q4", "on": "2027-01-12"}})
    store.save({"symbol": "VCB", "fetched_at": "2027-01-14T00:00:00+00:00", "source": "t", "years": {}, "quarters": {}, "dividends": [], "issues": [],
                "latest_quarter_seen": {"quarter": "2026-Q3", "on": "2026-10-20"}})
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=SyntheticMarket(prices={}), data_dir=tmp_path)
    rows = {r["symbol"]: r for r in call(TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock, "GET",
                                          "/internal/fairvalue").json()["rows"]}
    assert rows["FPT"]["quality"]["f_score"]["year"] == "2025" and rows["FPT"]["new_quarter"] == "2026-Q4"  # seen 3 days before the clock
    assert rows["VCB"]["quality"]["f_score"] is None and rows["VCB"]["new_quarter"] is None  # a bank without sector ratios yet


def test_fairvalue_scores_a_bank_from_its_stored_sector_ratios(tmp_path):
    from investment_agent.market.financial_ratios import FinancialRatioStore
    (tmp_path / "market-symbols.txt").write_text("VCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2, "sectors": {"VCB": "Ngân hàng"}}),
                                              encoding="utf-8")
    FinancialRatioStore(tmp_path / "financial-ratios").save({"symbol": "VCB", "kind": "bank", "fetched_at": "2026-10-31T00:00:00+00:00", "source": "t",
                                                             "quarters": {"2025-09-30": {"BAD_LOANS_RATIO_AQ": "0.0103"},
                                                                          "2026-09-30": {"BAD_LOANS_RATIO_AQ": "0.0071"}}})
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=SyntheticMarket(prices={}), data_dir=tmp_path)
    [row] = call(TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock, "GET", "/internal/fairvalue").json()["rows"]
    assert row["quality"]["f_score"]["kind"] == "health" and row["quality"]["f_score"]["score"] == 1


def test_forward_scenario_is_saved_per_ticker_and_priced_on_its_own_monthly_bands(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    years = {str(y): {"npat": "1000000000", "eps": "1000", "equity": "10000000000"} for y in range(2018, 2026)}
    FundamentalsStore(tmp_path / "fundamentals").save({"symbol": "FPT", "fetched_at": "2026-10-26T00:00:00+00:00", "source": "t",
                                                      "years": years, "quarters": {}, "dividends": [], "issues": []})
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(2025, m, 28), str(10 + m % 3)) for m in range(1, 13)])
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=SyntheticMarket(prices={"FPT": PricePoint(Decimal(12000), date(2027, 1, 14))}), data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    empty = call(c, clock, "GET", "/internal/fairvalue/forward/FPT").json()
    assert empty["version"] == 0 and empty["assumptions"] is None and empty["base"]["eps"] == "1000.00" and empty["years"] == []
    body = {"assumptions": {"profit_growth": ["0.1", "0.1"], "equity_growth": ["0.1", "0.1"], "dilution": ["0", "0"]}, "custom": {"pe": "10", "pb": None},
            "expected_version": 0, "request_id": "f1"}
    out = call(c, clock, "PUT", "/internal/fairvalue/forward/FPT", body).json()
    assert out["version"] == 1 and [y["year"] for y in out["years"]] == ["2026", "2027"] and out["years"][0]["eps"] == "1100.00"
    assert out["years"][0]["custom"]["pe"] == "11000.00" and len(out["years"][0]["pe"]) == 7
    assert call(c, clock, "GET", "/internal/fairvalue/forward/FPT").json()["assumptions"]["profit_growth"] == ["0.1", "0.1"]
    bad = {**body, "assumptions": {**body["assumptions"], "profit_growth": ["9", "0.1"]}, "expected_version": 1, "request_id": "f2"}
    assert call(c, clock, "PUT", "/internal/fairvalue/forward/FPT", bad).status_code == 422
    assert call(c, clock, "GET", "/internal/fairvalue/forward/ZZZ").status_code == 404


def _app(tmp_path, prices=None):
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=SyntheticMarket(prices=prices or {}), data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock


def test_sector_ratios_list_a_financial_ticker_quarters_oldest_first_with_labels(tmp_path):
    from investment_agent.market.financial_ratios import FinancialRatioStore
    (tmp_path / "market-symbols.txt").write_text("VCB\nFPT\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"VCB": "Ngân hàng", "FPT": "Công nghệ Thông tin"}}), encoding="utf-8")
    FinancialRatioStore(tmp_path / "financial-ratios").save({"symbol": "VCB", "kind": "bank", "fetched_at": "2026-10-31T00:00:00+00:00", "source": "t",
                                                             "quarters": {"2026-09-30": {"BAD_LOANS_RATIO_AQ": "0.0071"}, "2026-06-30": {"BAD_LOANS_RATIO_AQ": "0.0061"}}})
    c, clock = _app(tmp_path)
    body = call(c, clock, "GET", "/internal/fairvalue/ratios/VCB").json()
    assert body["kind"] == "bank" and [q["label"] for q in body["quarters"]] == ["Q2/2026", "Q3/2026"]
    npl = next(m for m in body["metrics"] if m["code"] == "BAD_LOANS_RATIO_AQ")
    assert npl["label"] == "Tỷ lệ nợ xấu (NPL)" and npl["format"] == "pct2" and npl["values"] == ["0.0061", "0.0071"]
    assert call(c, clock, "GET", "/internal/fairvalue/ratios/FPT").status_code == 404


def test_dividend_history_route_uses_the_stored_record_and_the_current_price(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("ACB\n", encoding="utf-8")
    FundamentalsStore(tmp_path / "fundamentals").save({"symbol": "ACB", "fetched_at": "2027-01-14T00:00:00+00:00", "source": "t",
                                                      "years": {"2025": {"eps": "5000"}}, "quarters": {}, "issues": [],
                                                      "dividends": [{"date": "2026-06-15", "cash": "700"}],
                                                      "share_issues": [{"date": "2026-06-15", "kind": "bonus", "ratio": "0.13"}]})
    c, clock = _app(tmp_path, {"ACB": PricePoint(Decimal(21000), date(2027, 1, 14))})
    body = call(c, clock, "GET", "/internal/fairvalue/dividends/ACB").json()
    assert body["years"][0] == {"year": "2026", "cash": "700", "stock": "0.13", "eps_prev": "5000", "payout": "0.1400", "stock_note": None}
    assert body["ttm"]["cash"] == "700" and body["ttm"]["yield"] == "0.0333"
    assert call(c, clock, "GET", "/internal/fairvalue/dividends/ZZZ").status_code == 404
