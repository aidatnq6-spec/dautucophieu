import json
from datetime import datetime, timezone

import pandas as pd

from investment_agent.market.fundamentals import FundamentalsStore, build_record

NOW = datetime(2026, 10, 26, 13, tzinfo=timezone.utc)
NPAT, EPS, EQ = "IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY", "IS_BASIC_EARNINGS_PER_SHARE", "BS_EQUITY"


def rows(period, **ids):
    return [{"period": period, "id": k, "name": "x", "value": v} for k, v in ids.items()]


FRAMES = {
    "income_year": rows("2024", **{NPAT: 1.5e9, EPS: 1500.0}) + rows("2025", **{NPAT: 2.0e9, EPS: 2000.0, "IS_NET_REVENUE": 9e9}),
    "balance_year": rows("2024", **{EQ: 13e9}) + rows("2025", **{EQ: 15e9}),
    "income_quarter": rows("2026-Q1", **{NPAT: 5.5e8}) + rows("2026-Q2", **{NPAT: float("nan")}),
    "balance_quarter": rows("2026-Q2", **{EQ: 16e9}),
    "events": [
        {"event_code": "DIV", "event_title_vi": "Trả cổ tức bằng tiền mặt - Đợt 1 2025 - 1,000 VND", "exright_date": pd.Timestamp("2025-12-01", tz="Asia/Ho_Chi_Minh")},
        {"event_code": "DIV", "event_title_vi": "Trả cổ tức bằng tiền mặt - Đợt 2 2025 - 1,500 VND", "exright_date": pd.NaT},
        {"event_code": "ISS", "event_title_vi": "Phát hành cổ phiếu - Cổ phiếu thưởng tỉ lệ 10.0%", "exright_date": pd.Timestamp("2026-09-21", tz="Asia/Ho_Chi_Minh")},
        {"event_code": "AGME", "event_title_vi": "Đại hội cổ đông", "exright_date": pd.Timestamp("2026-04-01", tz="Asia/Ho_Chi_Minh")},
    ],
}


def test_record_keeps_only_the_needed_lines_and_parses_events():
    r = build_record("fpt", FRAMES, NOW)
    assert r["symbol"] == "FPT" and r["fetched_at"] == NOW.isoformat() and r["source"] == "vnstock:vci"
    assert r["years"] == {"2024": {"npat": "1500000000", "eps": "1500", "equity": "13000000000"},
                          "2025": {"npat": "2000000000", "eps": "2000", "equity": "15000000000"}}
    assert r["quarters"] == {"2026-Q1": {"npat": "550000000"}, "2026-Q2": {"equity": "16000000000"}}  # NaN dropped
    assert r["dividends"] == [{"date": "2025-12-01", "cash": "1000"}]  # undated event skipped
    assert r["issues"] == [{"date": "2026-09-21", "ratio": "0.1"}]


def test_store_round_trips_and_lists_stale_tickers_oldest_first(tmp_path):
    s = FundamentalsStore(tmp_path / "fundamentals")
    s.save(build_record("FPT", FRAMES, datetime(2026, 10, 10, tzinfo=timezone.utc)))
    s.save(build_record("MBB", FRAMES, datetime(2026, 10, 25, tzinfo=timezone.utc)))
    assert s.read("FPT")["years"]["2025"]["eps"] == "2000" and s.read("VCB") is None
    assert s.stale(["MBB", "FPT", "VCB"], now=NOW, max_age_days=7) == ["VCB", "FPT"]  # missing first, then oldest


from datetime import date, timedelta

from investment_agent.market.fundamentals import sync_fundamentals
from investment_agent.market.series import SeriesStore


class FakeProvider:
    def __init__(self, fail_once=()):
        self.calls, self.fail = [], set(fail_once)

    def fundamentals_frames(self, symbol):
        self.calls.append(("frames", symbol))
        if symbol in self.fail:
            self.fail.discard(symbol)
            raise RuntimeError("60/60 lượt gọi")
        return FRAMES

    def fetch_closes(self, symbol, start, end, *, interval, index):
        self.calls.append(("closes", symbol, start))
        return [(datetime(2025, 12, 31), "26")]


def test_sync_refreshes_the_stalest_tickers_and_their_daily_closes(tmp_path):
    store, series, p, waits = FundamentalsStore(tmp_path / "f"), SeriesStore(tmp_path / "s"), FakeProvider(fail_once={"MBB"}), []
    out = sync_fundamentals(store, series, ["MBB", "FPT", "VCB"], provider=p, now=NOW, limit=2, sleep=waits.append)
    assert out == {"updated": ["FPT", "MBB"], "errors": {}} or out == {"updated": ["MBB", "FPT"], "errors": {}}
    assert store.read("VCB") is None and 65 in waits  # MBB failed once, waited, then succeeded
    assert ("closes", "FPT", NOW.date() - timedelta(days=2920)) in p.calls and series.read("FPT-1d")


def test_sync_records_a_second_failure_and_moves_on(tmp_path):
    class Broken(FakeProvider):
        def fundamentals_frames(self, symbol):
            raise RuntimeError("down")
    out = sync_fundamentals(FundamentalsStore(tmp_path / "f"), SeriesStore(tmp_path / "s"), ["MBB"], provider=Broken(), now=NOW, limit=8,
                            sleep=lambda s: None)
    assert out == {"updated": [], "errors": {"MBB": "error:RuntimeError"}}


def test_cli_fundamentals_sync_reads_the_watchlist(tmp_path, capsys):
    from investment_agent.cli import fundamentals_sync
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    assert fundamentals_sync(tmp_path, limit=8, provider=FakeProvider(), now=NOW, sleep=lambda s: None) == 0
    assert '"updated": ["FPT"]' in capsys.readouterr().out


def test_securities_firms_fall_back_to_net_profit_and_listed_shares():
    # Securities firms (e.g. SSI) report no parent-company profit line and no EPS (checked 2026-10-26).
    frames = {**FRAMES, "income_year": rows("2025", IS_NET_PROFIT_AFTER_TAX=4.1e9), "income_quarter": rows("2026-Q2", IS_NET_PROFIT_AFTER_TAX=1.2e9),
              "overview": [{"outstanding_shares": 3001302333.0, "issue_share": 3003293801}]}
    r = build_record("SSI", frames, NOW)
    assert r["years"]["2025"]["npat"] == "4100000000" and r["quarters"]["2026-Q2"]["npat"] == "1200000000"
    assert r["shares_outstanding"] == "3001302333"
    parent = build_record("FPT", {**FRAMES, "income_year": FRAMES["income_year"] + rows("2025", IS_NET_PROFIT_AFTER_TAX=9e9)}, NOW)
    assert parent["years"]["2025"]["npat"] == "2000000000"  # the parent-company line wins when both exist


def test_cli_can_refresh_named_tickers_now_even_when_recent(tmp_path, capsys):
    from investment_agent.cli import fundamentals_sync
    (tmp_path / "market-symbols.txt").write_text("FPT\nSSI\n", encoding="utf-8")
    FundamentalsStore(tmp_path / "fundamentals").save(build_record("SSI", FRAMES, NOW))  # fresh, so not stale
    assert fundamentals_sync(tmp_path, limit=8, symbols=["SSI"], provider=FakeProvider(), now=NOW, sleep=lambda s: None) == 0
    assert '"updated": ["SSI"]' in capsys.readouterr().out


def test_record_keeps_the_annual_lines_for_report_quality_and_share_issue_kinds():
    frames = {**FRAMES,
              "income_year": FRAMES["income_year"] + rows("2025", IS_GROSS_PROFIT=3e9, IS_SELLING_EXPENSES=4e8, IS_GENERAL_AND_ADMINISTRATIVE_EXPENSES=5e8,
                                                          IS_NET_PROFIT_AFTER_TAX=2.2e9),
              "balance_year": FRAMES["balance_year"] + rows("2025", BS_TOTAL_ASSETS=40e9, BS_SHORT_TERM_ASSETS=20e9, BS_SHORT_TERM_LIABILITIES=10e9,
                                                            BS_LONG_TERM_LIABILITIES=5e9, BS_SHORT_TERM_RECEIVABLES=6e9),
              "cash_year": rows("2025", CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES=-1e9, CF_NET_CASH_FLOWS_DURING_THE_PERIOD=2e8),
              "events": FRAMES["events"] + [
                  {"event_code": "ISS", "event_title_vi": "Phát hành cổ phiếu - Phát hành cho CBCNV tỉ lệ 0.5%", "exright_date": pd.Timestamp("2025-06-05")},
                  {"event_code": "ISS", "event_title_vi": "Phát hành cổ phiếu - Quyền mua CP cho Cổ đông hiện hữu tỉ lệ 20.0%",
                   "exright_date": pd.Timestamp("2025-12-08")},
                  {"event_code": "ISS", "event_title_vi": "Phát hành cổ phiếu - Trả Cổ tức bằng Cổ phiếu tỉ lệ 10.0%", "exright_date": pd.Timestamp("2024-05-25")},
                  {"event_code": "ISS", "event_title_vi": "Phát hành cổ phiếu - Hoán đổi", "exright_date": pd.Timestamp("2024-02-01")}]}
    r = build_record("FPT", frames, NOW)
    assert r["years"]["2025"] == {"npat": "2000000000", "eps": "2000", "equity": "15000000000"}  # valuation lines unchanged
    assert r["annual"]["2025"] == {"revenue": "9000000000", "gross_profit": "3000000000", "selling": "400000000", "admin": "500000000",
                                   "profit": "2200000000", "total_assets": "40000000000", "current_assets": "20000000000",
                                   "current_liabilities": "10000000000", "long_liabilities": "5000000000", "receivables": "6000000000",
                                   "cfo": "-1000000000"}
    assert r["share_issues"] == [{"date": "2024-02-01", "kind": "other"}, {"date": "2024-05-25", "kind": "bonus"},
                                 {"date": "2025-06-05", "kind": "raise"}, {"date": "2025-12-08", "kind": "raise"},
                                 {"date": "2026-09-21", "kind": "bonus"}]


def test_sync_notes_the_day_a_new_latest_quarter_first_appears(tmp_path):
    store, series = FundamentalsStore(tmp_path / "f"), SeriesStore(tmp_path / "s")
    sync_fundamentals(store, series, ["FPT"], provider=FakeProvider(), now=NOW, limit=None, max_age_days=0, sleep=lambda s: None)
    assert store.read("FPT")["latest_quarter_seen"] == {"quarter": "2026-Q1", "on": "2026-10-26"}
    later = datetime(2026, 11, 2, tzinfo=timezone.utc)
    sync_fundamentals(store, series, ["FPT"], provider=FakeProvider(), now=later, limit=None, max_age_days=0, sleep=lambda s: None)
    assert store.read("FPT")["latest_quarter_seen"] == {"quarter": "2026-Q1", "on": "2026-10-26"}  # same quarter: first day kept


def test_cli_refreshes_more_often_in_the_months_reports_are_due(tmp_path, capsys):
    from investment_agent.cli import fundamentals_sync
    names = [f"A{i:02d}" for i in range(20)]
    (tmp_path / "market-symbols.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    store = FundamentalsStore(tmp_path / "fundamentals")
    for s in names:  # all fetched four days before: stale only in a reporting month (3 days), not otherwise (7 days)
        store.save(build_record(s, FRAMES, datetime(2026, 10, 22, tzinfo=timezone.utc)))
    fundamentals_sync(tmp_path, limit=8, provider=FakeProvider(), now=NOW, sleep=lambda s: None)  # October: reports due
    assert len(json.loads(capsys.readouterr().out)["updated"]) == 17
    for s in names:
        store.save(build_record(s, FRAMES, datetime(2026, 12, 1, tzinfo=timezone.utc)))
    fundamentals_sync(tmp_path, limit=8, provider=FakeProvider(), now=datetime(2026, 12, 5, tzinfo=timezone.utc), sleep=lambda s: None)
    assert json.loads(capsys.readouterr().out)["updated"] == []  # December: 7 days
