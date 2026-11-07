import json
from datetime import date, datetime, timezone

from investment_agent.market.statements import StatementStore, parse_statements, sync_statements


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
        kind = "ANNUAL" if "ANNUAL" in url else "QUARTER"
        sym = url.split("code:")[1].split("~")[0]
        fiscal = "2025-12-31"
        return text(row(21001, 1e12 if kind == "QUARTER" else 4e12, fiscal, code=sym, kind=kind))


NOW = datetime(2026, 11, 7, 3, tzinfo=timezone.utc)


def test_sync_takes_the_whole_history_once_then_two_years_merged_skipping_financials_and_stale_first(tmp_path):
    store, get = StatementStore(tmp_path), Get()
    sectors = {"HPG": "Tài nguyên Cơ bản", "FPT": "Công nghệ Thông tin", "VCB": "Ngân hàng"}
    out = sync_statements(store, sectors, get=get, now=NOW, limit=None, sleep=lambda s: None)
    assert out == {"FPT": "ok", "HPG": "ok"} and store.read("VCB") is None
    assert all("fiscalDate:gte:2010-01-01" in u for u in get.urls) and len(get.urls) == 4
    rec = store.read("HPG")
    assert rec["quarters"] == {"2025-Q4": {"revenue": "1000000000000"}} and rec["years"] == {"2025": {"revenue": "4000000000000"}}
    assert rec["source"] == "vndirect:finfo" and rec["fetched_at"] == NOW.isoformat()
    rec["quarters"]["2015-Q1"] = {"revenue": "5"}
    rec["fetched_at"] = "2026-11-01T00:00:00+00:00"  # older than FPT's, so HPG is the stalest
    store.save(rec)
    get2 = Get()
    later = datetime(2026, 11, 20, tzinfo=timezone.utc)
    sync_statements(store, sectors, get=get2, now=later, limit=1, sleep=lambda s: None)
    assert len(get2.urls) == 2 and all("code:HPG~" in u and "fiscalDate:gte:2024-11-20" in u for u in get2.urls)  # the stalest, two years back
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
    assert json.loads(capsys.readouterr().out) == {"status": "ok", "results": {"HPG": "ok"}}
    assert StatementStore(tmp_path / "statements").read("HPG")["years"] == {"2025": {"revenue": "4000000000000"}}
