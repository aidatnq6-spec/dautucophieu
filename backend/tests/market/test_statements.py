import json
from datetime import date, datetime, timezone

from investment_agent.market.statements import LINES_VERSION, StatementStore, parse_statements, parse_year_end_closes, sync_statements


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


def test_each_period_keeps_the_latest_day_the_source_updated_it():
    """Owner, 23/11/2026: VNDirect's year first shows the company's own Q4 figures and is updated with the audited ones later
    (modifiedDate); the latest update of any line is kept per period, and a later sync moves it on."""
    r1, r2 = row(23800, 4.876e12, "2025-12-31", kind="ANNUAL"), row(11490, -4.058e11, "2025-12-31", model=1, kind="ANNUAL")
    r1["modifiedDate"], r2["modifiedDate"] = "2026-04-01 00:00:00", "2026-07-31 00:00:00"
    out = parse_statements(text(r1, r2, row(21001, 1, "2024-12-31", kind="ANNUAL")), symbol="HPG", kind="ANNUAL")
    assert out["modified"] == {"2025": "2026-07-31"}  # a row without modifiedDate gives none


def test_the_general_layout_reads_its_whole_history_again_once_for_the_update_days():
    """Review 23/11/2026 (tồn kho): the update days only came with the 2-year refresh, so 2021–2023 could never be compared; version 7
    makes each ticker read its whole history once."""
    from investment_agent.market.statements import LINES_VERSION
    assert LINES_VERSION >= 7


def test_a_reread_for_a_version_with_the_same_lines_still_logs_revisions(tmp_path):
    """Review 23/11/2026 (4): version 7 re-reads the history with the lines of version 6, so a figure the source changed is still logged."""
    from investment_agent.market.statement_revisions import read_revisions
    store = StatementStore(tmp_path / "statements")
    store.save({"symbol": "HPG", "fetched_at": "2026-11-06T00:00:00+00:00", "source": "vndirect:finfo", "lines_version": 6,
                "quarters": {}, "years": {"2024": {"npat_parent": str(100 * 10**9)}, "2025": {"npat_parent": str(150 * 10**9)}},
                "year_end_close": {}, "quarter_end_close": {}})

    def get(url):
        if "stock_prices" in url:
            return json.dumps({"data": []})
        if "ANNUAL" in url:
            return text(row(23000, 8e10, "2024-12-31", kind="ANNUAL"), row(23000, 1.5e11, "2025-12-31", kind="ANNUAL"))
        return text()
    sync_statements(store, {"HPG": "Tài nguyên Cơ bản"}, get=get, now=NOW, limit=None, sleep=lambda s: None)
    assert [(r["period"], r["line"]) for r in read_revisions(tmp_path, "HPG")] == [("2024", "npat_parent")]


def test_sync_keeps_the_update_days_by_period(tmp_path):
    def get(url):
        if "stock_prices" in url:
            return json.dumps({"data": []})
        r = row(21001, 1e12, "2025-12-31", kind="ANNUAL" if "ANNUAL" in url else "QUARTER")
        r["modifiedDate"] = "2026-04-01 00:00:00"
        return text(r)
    store = StatementStore(tmp_path)
    sync_statements(store, {"HPG": "Tài nguyên Cơ bản"}, get=get, now=NOW, limit=None, sleep=lambda s: None)
    rec = store.read("HPG")
    assert rec["years_modified"] == {"2025": "2026-04-01"} and rec["quarters_modified"] == {"2025-Q4": "2026-04-01"}


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
    store.save({"symbol": "HPG", "fetched_at": "2026-10-01T00:00:00+00:00", "source": "vndirect:finfo", "quarters": {}, "years": {},
                "lines_version": LINES_VERSION})  # its lines are current: only the closes are missing
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


def test_a_bank_keeps_its_loans_reserve_accrued_interest_interest_income_and_provision_expense():
    """Chất lượng tài sản ngân hàng (owner, 23/11/2026), part 1: the TT49 lines of VNDirect, VCB Q3/2026 in tỷ đồng."""
    from investment_agent.market.statements import FIN_LINES_VERSION, LAYOUTS
    assert FIN_LINES_VERSION >= 3
    page = text(row(412100, 1.8160933e15, "2026-09-30", model=101, code="VCB"), row(412200, -3.11681e13, "2026-09-30", model=101, code="VCB"),
                row(412520, 1.18111e13, "2026-09-30", model=101, code="VCB"), row(421100, 4.00146e13, "2026-09-30", model=102, code="VCB"),
                row(422900, 6.1841e12, "2026-09-30", model=102, code="VCB"))
    out = parse_statements(page, symbol="VCB", kind="QUARTER", lines=LAYOUTS["bank"]["lines"], zero_missing=LAYOUTS["bank"]["zero_missing"])
    assert out["periods"] == {"2026-Q3": {"loans_gross": "1816093300000000", "loan_reserve": "-31168100000000", "accrued_interest": "11811100000000",
                                          "interest_income": "40014600000000", "provision_expense": "6184100000000"}}
    assert out["zeros"] == []


def test_a_bank_balance_the_source_gives_as_zero_is_missing_and_said_so_while_a_zero_provision_expense_is_kept():
    from investment_agent.market.statements import LAYOUTS
    page = text(row(412100, 7.216e12, "2006-09-30", model=101, code="ACB"), row(412200, 0, "2006-09-30", model=101, code="ACB"),
                row(412520, 0, "2006-09-30", model=101, code="ACB"), row(422900, 0, "2006-09-30", model=102, code="ACB"))
    out = parse_statements(page, symbol="ACB", kind="QUARTER", lines=LAYOUTS["bank"]["lines"], zero_missing=LAYOUTS["bank"]["zero_missing"])
    assert out["periods"] == {"2006-Q3": {"loans_gross": "7216000000000", "provision_expense": "0"}}
    assert out["zeros"] == [{"period": "2006-Q3", "line": "accrued_interest"}, {"period": "2006-Q3", "line": "loan_reserve"}]
    assert parse_statements(page, symbol="ACB", kind="QUARTER", lines=LAYOUTS["bank"]["lines"])["zeros"] == []  # only where the layout says


def test_sync_keeps_the_zero_balances_of_a_bank_by_period_and_a_later_figure_clears_them(tmp_path):
    def get(url):
        if "stock_prices" in url:
            return json.dumps({"data": []})
        if "ANNUAL" in url:
            return text()
        return text(row(412520, 0, "2026-06-30", model=101, code="VCB"), row(412520, 5e12, "2026-09-30", model=101, code="VCB"))
    store = StatementStore(tmp_path)
    assert sync_statements(store, {"VCB": "Ngân hàng"}, get=get, now=NOW, limit=None, sleep=lambda s: None, kinds=("bank",)) == {"VCB": "ok"}
    rec = store.read("VCB")
    assert rec["quarters"] == {"2026-Q3": {"accrued_interest": "5000000000000"}}
    assert rec["quarters_zeros"] == [{"period": "2026-Q2", "line": "accrued_interest"}] and rec["years_zeros"] == []
    later = lambda url: (json.dumps({"data": []}) if "stock_prices" in url else text() if "ANNUAL" in url
                         else text(row(412520, 4e12, "2026-06-30", model=101, code="VCB")))
    sync_statements(store, {"VCB": "Ngân hàng"}, get=later, now=NOW.replace(year=2027), limit=None, sleep=lambda s: None, kinds=("bank",))
    rec = store.read("VCB")
    assert rec["quarters"]["2026-Q2"] == {"accrued_interest": "4000000000000"} and rec["quarters_zeros"] == []


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


def test_customer_advances_and_inventory_are_kept_from_the_balance_sheet():
    parsed = parse_statements(text(row(13130, 6e11, "2026-09-30", model=1), row(13311, 1e11, "2026-09-30", model=1), row(11400, 9e12, "2026-09-30", model=1)),
                              symbol="HPG", kind="QUARTER")
    assert parsed["periods"]["2026-Q3"] == {"advances_st": "600000000000", "advances_lt": "100000000000", "inventory": "9000000000000"}


def test_a_ticker_kept_before_the_advances_lines_is_due_and_takes_its_whole_history_once(tmp_path):
    store = StatementStore(tmp_path)
    store.save({"symbol": "HPG", "fetched_at": "2026-11-06T00:00:00+00:00", "source": "vndirect:finfo", "quarters": {"2015-Q1": {"revenue": "5"}},
                "years": {}, "year_end_close": {"2024": {"date": "2024-12-31", "close": "20"}},
                "quarter_end_close": {"2024-Q4": {"date": "2024-12-31", "close": "20"}}})  # recent, but without the newer lines
    get = Get()
    assert sync_statements(store, {"HPG": "Tài nguyên Cơ bản"}, get=get, now=NOW, limit=None, sleep=lambda s: None) == {"HPG": "ok"}
    assert all("fiscalDate:gte:2010-01-01" in u for u in get.urls if "financial_statements" in u)
    assert store.read("HPG")["lines_version"] >= 2
    get2 = Get()
    assert sync_statements(store, {"HPG": "Tài nguyên Cơ bản"}, get=get2, now=NOW, limit=None, sleep=lambda s: None) == {} and get2.urls == []


def test_a_bank_follows_its_own_layout_version(tmp_path):
    from investment_agent.market.statements import FIN_LINES_VERSION
    store = StatementStore(tmp_path)
    base = {"symbol": "VCB", "fetched_at": "2026-11-06T00:00:00+00:00", "source": "vndirect:finfo", "kind": "bank", "quarters": {}, "years": {},
            "year_end_close": {}, "quarter_end_close": {}}
    store.save({**base, "lines_version": FIN_LINES_VERSION})
    get = Get()
    assert sync_statements(store, {"VCB": "Ngân hàng"}, get=get, now=NOW, limit=None, sleep=lambda s: None, kinds=("bank",)) == {} and get.urls == []
    store.save(base)  # kept before EPS was taken
    assert sync_statements(store, {"VCB": "Ngân hàng"}, get=Get(), now=NOW, limit=None, sleep=lambda s: None, kinds=("bank",)) == {"VCB": "ok"}
    assert store.read("VCB")["lines_version"] == FIN_LINES_VERSION


def test_a_closed_years_figure_changed_by_the_source_is_logged_not_just_overwritten(tmp_path):
    """Số đã công bố bị sửa (owner, 22/11/2026): the sync logs the change in data/statement-revisions before it overwrites."""
    from investment_agent.market.statement_revisions import read_revisions

    def get(url):
        if "stock_prices" in url:
            return json.dumps({"data": []})
        kind = "ANNUAL" if "ANNUAL" in url else "QUARTER"
        return text(row(23000, 8e10, "2024-12-31", kind=kind, code="HAG"), row(23000, 1.5e11, "2025-12-31", kind=kind, code="HAG"))
    store = StatementStore(tmp_path / "statements")
    store.save({"symbol": "HAG", "fetched_at": "2026-10-01T00:00:00+00:00", "lines_version": LINES_VERSION, "year_end_close": {"2025": {}},
                "quarter_end_close": {}, "years": {"2024": {"npat_parent": "100000000000"}, "2025": {"npat_parent": "150000000000"}},
                "quarters": {"2024-Q4": {"npat_parent": "100000000000"}, "2025-Q4": {"npat_parent": "150000000000"}}})
    out = sync_statements(store, {"HAG": "Thực phẩm và đồ uống"}, get=get, now=NOW, limit=None, sleep=lambda s: None)
    assert out == {"HAG": "ok"} and store.read("HAG")["years"]["2024"]["npat_parent"] == "80000000000"
    assert {(r["kind"], r["period"], r["old"], r["new"], r["seen_on"]) for r in read_revisions(tmp_path, "HAG")} == {
        ("years", "2024", "100000000000", "80000000000", "2026-11-07"), ("quarters", "2024-Q4", "100000000000", "80000000000", "2026-11-07")}


def test_construction_in_progress_takes_the_layout_that_has_a_figure_and_two_figures_are_a_conflict():
    """XDCB dở dang: 12460 from 2015, 12300 before; the one that is not 0 is kept, both non-zero and different is a conflict."""
    out = parse_statements(text(row(12460, 0, "2013-12-31", model=1, kind="ANNUAL"), row(12300, 5e11, "2013-12-31", model=1, kind="ANNUAL"),
                                row(12460, 8.2893e12, "2021-12-31", model=1, kind="ANNUAL"), row(12300, 0, "2021-12-31", model=1, kind="ANNUAL"),
                                row(12460, 0, "2022-12-31", model=1, kind="ANNUAL"), row(12300, 0, "2022-12-31", model=1, kind="ANNUAL"),
                                row(12460, 3e11, "2014-12-31", model=1, kind="ANNUAL"), row(12300, 4e11, "2014-12-31", model=1, kind="ANNUAL")),
                           symbol="HPG", kind="ANNUAL")
    p = out["periods"]
    assert p["2013"] == {"cip": "500000000000"} and p["2021"] == {"cip": "8289300000000"} and p["2022"] == {"cip": "0"}
    assert "2014" not in p or "cip" not in p["2014"]
    assert {"period": "2014", "line": "cip", "values": ["300000000000", "400000000000"]} in out["conflicts"]
