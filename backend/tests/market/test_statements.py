import json
from datetime import date, datetime, timezone

from investment_agent.market.statements import StatementStore, parse_statements, parse_year_end_closes, sync_statements


def row(item, value, fiscal, model=2, created="2026-10-29 00:00:00", code="HPG", kind="QUARTER"):
    return {"code": code, "itemCode": float(item), "reportType": kind, "modelType": float(model), "numericValue": value, "fiscalDate": fiscal,
            "createdDate": created}


def text(*rows):
    return json.dumps({"data": list(rows)})


def test_rows_become_periods_with_named_lines_and_the_day_they_first_appeared():
    out = parse_statements(text(row(21001, 6.2214e13, "2026-09-30"), row(22510, 1.774e12, "2026-09-30"), row(32100, -2.0836e12, "2026-09-30", model=3),
                                row(13110, 7.8615e13, "2026-09-30", model=1, created="2026-10-30 00:00:00"), row(99999, 1, "2026-09-30"),
                                row(21001, 1, "2026-09-30", code="FPT")), symbol="HPG", kind="QUARTER")
    assert out["periods"] == {"2026-Q3": {"revenue": "62214000000000", "interest": "1774000000000", "capex": "-2083600000000", "st_debt": "78615000000000"}}
    assert out["created"] == {"2026-Q3": "2026-10-29"} and out["conflicts"] == []


def test_years_are_keyed_by_year_and_two_different_values_for_one_line_are_a_conflict_not_a_choice():
    out = parse_statements(text(row(22230, 5.994e11, "2012-12-31", model=3, kind="ANNUAL"), row(22230, 5.962e11, "2012-12-31", model=3, kind="ANNUAL"),
                                row(21001, 1.68e13, "2012-12-31", kind="ANNUAL"), row(21001, 1.68e13, "2012-12-31", kind="ANNUAL")),
                           symbol="HPG", kind="ANNUAL")
    assert out["periods"] == {"2012": {"revenue": "16800000000000"}}  # the same value twice is no conflict
    assert out["conflicts"] == [{"period": "2012", "line": "depreciation", "values": ["596200000000", "599400000000"]}]


def test_older_layouts_fill_the_same_lines():
    out = parse_statements(text(row(23200, 5e9, "2014-12-31", kind="ANNUAL"), row(15000, 7e9, "2014-12-31", model=1, kind="ANNUAL")),
                           symbol="HPG", kind="ANNUAL")
    assert out["periods"] == {"2014": {"associates": "5000000000", "minority_equity_outside": "7000000000"}}


class Get:
    def __init__(self, fail=()):
        self.urls, self.fail = [], set(fail)

    def __call__(self, url):
        self.urls.append(url)
        if any(f"code:{s}~" in url for s in self.fail):
            raise RuntimeError("offline")
        sym = url.split("code:")[1].split("~")[0].split("&")[0]
        if "stock_prices" in url:
            return json.dumps({"data": [{"code": sym, "date": "2025-12-31", "close": 26.4}, {"code": sym, "date": "2025-12-30", "close": 26.5}]})
        kind = "ANNUAL" if "ANNUAL" in url else "QUARTER"
        fiscal = "2025-12-31"
        models = {"modelType:101": 102, "modelType:89": 90, "modelType:411": 412}  # bank, securities, insurer: their income statement model
        for key, model in models.items():
            if key in url:
                return text(row(23000, 1e11, fiscal, model=model, code=sym, kind=kind))
        return text(row(21001, 1e12 if kind == "QUARTER" else 4e12, fiscal, code=sym, kind=kind))


NOW = datetime(2026, 11, 7, 3, tzinfo=timezone.utc)


def test_sync_takes_the_whole_history_once_then_two_years_merged_skipping_financials_and_stale_first(tmp_path):
    store, get = StatementStore(tmp_path), Get()
    sectors = {"HPG": "Tài nguyên Cơ bản", "FPT": "Công nghệ Thông tin", "VCB": "Ngân hàng"}
    out = sync_statements(store, sectors, get=get, now=NOW, limit=None, sleep=lambda s: None)
    assert out == {"FPT": "ok", "HPG": "ok"} and store.read("VCB") is None
    assert len(get.urls) == 6 and all("fiscalDate:gte:2010-01-01" in u or "date:gte:2010-01-01" in u for u in get.urls)
    rec = store.read("HPG")
    assert rec["quarters"] == {"2025-Q4": {"revenue": "1000000000000"}} and rec["years"] == {"2025": {"revenue": "4000000000000"}}
    assert rec["source"] == "vndirect:finfo" and rec["fetched_at"] == NOW.isoformat()
    assert rec["year_end_close"] == {"2025": {"date": "2025-12-31", "close": "26.4"}}
    rec["quarters"]["2015-Q1"] = {"revenue": "5"}
    rec["fetched_at"] = "2026-11-01T00:00:00+00:00"  # older than FPT's, so HPG is the stalest
    store.save(rec)
    get2 = Get()
    later = datetime(2026, 11, 20, tzinfo=timezone.utc)
    sync_statements(store, sectors, get=get2, now=later, limit=1, sleep=lambda s: None)
    assert len(get2.urls) == 3 and all("code:HPG" in u and "ate:gte:2024-11-20" in u for u in get2.urls)  # the stalest, two years back
    assert store.read("HPG")["quarters"] == {"2015-Q1": {"revenue": "5"}, "2025-Q4": {"revenue": "1000000000000"}}  # older periods kept


def test_sync_reports_a_failing_ticker_and_goes_on(tmp_path):
    store = StatementStore(tmp_path)
    out = sync_statements(store, {"HPG": "Tài nguyên Cơ bản", "FPT": "Công nghệ Thông tin"}, get=Get(fail={"HPG"}), now=NOW, limit=None,
                          sleep=lambda s: None)
    assert out["FPT"] == "ok" and out["HPG"].startswith("error:") and store.read("HPG") is None


def test_recent_tickers_are_left_alone(tmp_path):
    store = StatementStore(tmp_path)
    sync_statements(store, {"HPG": "Tài nguyên Cơ bản"}, get=Get(), now=NOW, limit=None, sleep=lambda s: None)
    get = Get()
    assert sync_statements(store, {"HPG": "Tài nguyên Cơ bản"}, get=get, now=NOW, limit=None, sleep=lambda s: None) == {} and get.urls == []


def test_cli_statements_sync_reads_the_watchlist_and_sectors(tmp_path, capsys):
    from investment_agent.cli import statements_sync
    (tmp_path / "market-symbols.txt").write_text("HPG\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"HPG": "Tài nguyên Cơ bản", "VCB": "Ngân hàng"}}), encoding="utf-8")
    assert statements_sync(tmp_path, limit=5, get=Get(), now=NOW, sleep=lambda s: None) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "ok", "results": {"HPG": "ok", "VCB": "ok"}}  # the bank into statements-financial
    assert StatementStore(tmp_path / "statements").read("HPG")["years"] == {"2025": {"revenue": "4000000000000"}}


def test_the_last_unadjusted_close_of_each_year_is_kept_with_its_day():
    page = json.dumps({"data": [{"code": "HPG", "date": "2026-11-06", "close": 21.2}, {"code": "HPG", "date": "2025-12-31", "close": 26.4},
                                {"code": "HPG", "date": "2025-12-30", "close": 26.5}, {"code": "HPG", "date": "2018-12-28", "close": 30.95},
                                {"code": "FPT", "date": "2018-12-31", "close": 99}, {"code": "HPG", "date": "2017-12-29", "close": None}]})
    assert parse_year_end_closes(page, symbol="HPG") == {"2018": {"date": "2018-12-28", "close": "30.95"}, "2025": {"date": "2025-12-31", "close": "26.4"},
                                                         "2026": {"date": "2026-11-06", "close": "21.2"}}


def test_a_ticker_synced_before_year_end_closes_existed_takes_the_whole_price_history(tmp_path):
    store = StatementStore(tmp_path)
    store.save({"symbol": "HPG", "fetched_at": "2026-10-01T00:00:00+00:00", "source": "vndirect:finfo", "quarters": {}, "years": {}})
    get = Get()
    sync_statements(store, {"HPG": "Tài nguyên Cơ bản"}, get=get, now=NOW, limit=None, sleep=lambda s: None)
    prices = [u for u in get.urls if "stock_prices" in u]
    assert len(prices) == 1 and "date:gte:2010-01-01" in prices[0] and all("fiscalDate:gte:2024-11-07" in u for u in get.urls if u not in prices)


def test_the_last_unadjusted_close_of_each_quarter_is_kept_with_its_day():
    from investment_agent.market.statements import parse_quarter_end_closes
    page = json.dumps({"data": [{"code": "HPG", "date": "2025-12-31", "close": 26.4}, {"code": "HPG", "date": "2025-12-30", "close": 26.5},
                                {"code": "HPG", "date": "2025-09-30", "close": 29.1}, {"code": "HPG", "date": "2025-07-01", "close": 27},
                                {"code": "FPT", "date": "2025-03-31", "close": 99}]})
    assert parse_quarter_end_closes(page, symbol="HPG") == {"2025-Q3": {"date": "2025-09-30", "close": "29.1"},
                                                            "2025-Q4": {"date": "2025-12-31", "close": "26.4"}}


def test_sync_keeps_quarter_end_closes_and_a_ticker_without_them_is_due_and_takes_the_whole_price_history(tmp_path):
    store = StatementStore(tmp_path)
    store.save({"symbol": "HPG", "fetched_at": "2026-11-06T00:00:00+00:00", "source": "vndirect:finfo", "quarters": {}, "years": {},
                "year_end_close": {"2024": {"date": "2024-12-31", "close": "20"}}})
    get = Get()
    assert sync_statements(store, {"HPG": "Tài nguyên Cơ bản"}, get=get, now=NOW, limit=None, sleep=lambda s: None) == {"HPG": "ok"}
    prices = [u for u in get.urls if "stock_prices" in u]
    assert len(prices) == 1 and "date:gte:2010-01-01" in prices[0]
    rec = store.read("HPG")
    assert rec["quarter_end_close"] == {"2025-Q4": {"date": "2025-12-31", "close": "26.4"}}
    assert rec["year_end_close"]["2024"] == {"date": "2024-12-31", "close": "20"}
    get2 = Get()
    assert sync_statements(store, {"HPG": "Tài nguyên Cơ bản"}, get=get2, now=NOW, limit=None, sleep=lambda s: None) == {} and get2.urls == []


def test_bank_and_securities_layouts_keep_their_own_lines():
    from investment_agent.market.statements import LAYOUTS
    page = text(row(14110, 1e11, "2026-09-30", model=101, code="MBB"), row(14000, 1e12, "2026-09-30", model=101, code="MBB"),
                row(14240, 1e10, "2026-09-30", model=101, code="MBB"), row(88888, 5e10, "2026-09-30", model=102, code="MBB"),
                row(421701, 7e10, "2026-09-30", model=102, code="MBB"), row(23000, 3e10, "2026-09-30", model=102, code="MBB"),
                row(21001, 9e10, "2026-09-30", model=102, code="MBB"))  # a general-layout code under the bank model: not a bank line
    assert parse_statements(page, symbol="MBB", kind="QUARTER", lines=LAYOUTS["bank"]["lines"])["periods"] == {"2026-Q3": {
        "charter_capital": "100000000000", "equity": "1000000000000", "minority_equity": "10000000000", "ppop": "50000000000",
        "operating_income": "70000000000", "npat_parent": "30000000000"}}
    page = text(row(13110, 5e10, "2026-09-30", model=89, code="SSI"), row(13340, 0, "2026-09-30", model=89, code="SSI"),
                row(21000, 3e10, "2026-09-30", model=90, code="SSI"), row(23000, 1e10, "2026-09-30", model=90, code="SSI"))
    assert parse_statements(page, symbol="SSI", kind="QUARTER", lines=LAYOUTS["securities"]["lines"])["periods"] == {"2026-Q3": {
        "st_debt": "50000000000", "lt_debt": "0", "operating_revenue": "30000000000", "npat_parent": "10000000000"}}


def test_sync_of_financial_kinds_asks_for_their_models_and_skips_the_others(tmp_path):
    store, get = StatementStore(tmp_path), Get()
    sectors = {"HPG": "Tài nguyên Cơ bản", "MBB": "Ngân hàng", "SSI": "Dịch vụ tài chính", "BVH": "Bảo hiểm"}
    out = sync_statements(store, sectors, get=get, now=NOW, limit=None, sleep=lambda s: None, kinds=("bank", "securities"))
    assert out == {"MBB": "ok", "SSI": "ok"} and store.read("HPG") is None and store.read("BVH") is None
    statements = [u for u in get.urls if "financial_statements" in u]
    assert all("modelType:101,102,103" in u for u in statements if "code:MBB" in u)
    assert all("modelType:89,90,91" in u for u in statements if "code:SSI" in u)
    assert store.read("MBB")["kind"] == "bank" and store.read("SSI")["kind"] == "securities"
    assert sync_statements(StatementStore(tmp_path / "general"), sectors, get=Get(), now=NOW, limit=None, sleep=lambda s: None) == {"HPG": "ok"}


def test_a_page_filled_to_its_size_may_be_cut_and_is_not_kept(tmp_path, monkeypatch):
    import investment_agent.market.statements as st
    monkeypatch.setattr(st, "PAGE", 1)
    store = StatementStore(tmp_path)
    out = sync_statements(store, {"HPG": "Tài nguyên Cơ bản"}, get=Get(), now=NOW, limit=None, sleep=lambda s: None)
    assert out["HPG"].startswith("error:") and store.read("HPG") is None


def test_cli_statements_sync_keeps_banks_and_securities_apart(tmp_path, capsys):
    from investment_agent.cli import statements_sync
    (tmp_path / "market-symbols.txt").write_text("HPG\nMBB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"HPG": "Tài nguyên Cơ bản", "MBB": "Ngân hàng"}}), encoding="utf-8")
    assert statements_sync(tmp_path, limit=5, get=Get(), now=NOW, sleep=lambda s: None) == 0
    assert json.loads(capsys.readouterr().out)["results"] == {"HPG": "ok", "MBB": "ok"}
    assert StatementStore(tmp_path / "statements").read("MBB") is None
    assert StatementStore(tmp_path / "statements-financial").read("MBB")["kind"] == "bank"


def test_an_insurer_keeps_its_own_lines_with_both_associates_lines_apart():
    from investment_agent.market.statements import LAYOUTS
    page = text(row(21440, 9.59e12, "2026-09-30", model=412, code="BVH"), row(23110, -2.541e12, "2026-09-30", model=412, code="BVH"),
                row(22175, 3.515e12, "2026-09-30", model=412, code="BVH"), row(23200, 3.5e10, "2026-09-30", model=412, code="BVH"),
                row(23300, 0, "2026-09-30", model=412, code="BVH"), row(12500, 1.76e14, "2026-09-30", model=411, code="BVH"))
    assert parse_statements(page, symbol="BVH", kind="QUARTER", lines=LAYOUTS["insurance"]["lines"])["periods"] == {"2026-Q3": {
        "net_premium": "9590000000000", "ins_result": "-2541000000000", "fin_profit": "3515000000000", "associates_before": "35000000000",
        "associates": "0", "lt_investments": "176000000000000"}}


def test_sync_of_insurers_asks_for_their_models(tmp_path):
    get = Get()
    out = sync_statements(StatementStore(tmp_path), {"BVH": "Bảo hiểm", "MBB": "Ngân hàng"}, get=get, now=NOW, limit=None, sleep=lambda s: None,
                          kinds=("insurance",))
    assert out == {"BVH": "ok"} and all("modelType:411,412,413" in u for u in get.urls if "financial_statements" in u)
