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
