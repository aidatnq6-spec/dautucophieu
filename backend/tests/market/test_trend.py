import json
from datetime import date, datetime, timedelta, timezone

from investment_agent.market.calendar import TradingCalendar
from investment_agent.market.trend import FRAMES, SnapshotStore, build_cells, compare, load_board, run_trend

VN = timezone(timedelta(hours=7))
CAL = TradingCalendar(version="t", source="test", holidays=frozenset(), first=date(2016, 1, 1), last=date(2026, 12, 31))


def daily(n, end=date(2026, 10, 23), up=True):
    days = [d for d in CAL.sessions(end - timedelta(days=n * 2), end)][-n:]
    return [(datetime(d.year, d.month, d.day), 100.0 * (1.002 ** i if up else 0.998 ** i)) for i, d in enumerate(days)]  # accelerating rise


def hourly(n, end=date(2026, 10, 23)):
    out, day = [], end
    while len(out) < n:
        if CAL.is_session(day):
            out = [(datetime(day.year, day.month, day.day, h, tzinfo=VN), 0.0) for h in (9, 10, 11, 13, 14)] + out
        day -= timedelta(days=1)
    return [(t, 100.0 + i) for i, (t, _) in enumerate(out[-n:])]


def test_board_has_17_rows_in_three_groups():
    groups = load_board()
    assert [g["id"] for g in groups] == ["macro", "index", "stocks"] and sum(len(g["rows"]) for g in groups) == 17


def test_cells_cover_every_frame_and_explain_gaps():
    cells = build_cells(daily(1200), hourly(400), session_date=date(2026, 10, 23), hourly_supported=True)
    assert set(cells) == set(FRAMES) and cells["D1"]["macd"] == "up,>0" and cells["H1"]["rsi"] == 100
    assert cells["M"]["reason"] is None  # 1200 sessions are about 57 months
    short = build_cells(daily(200), [], session_date=date(2026, 10, 23), hourly_supported=True)
    assert short["M"]["reason"] == "Chưa đủ lịch sử" and short["H1"]["reason"] == "Chưa có dữ liệu"
    fred = build_cells(daily(1200), None, session_date=None, hourly_supported=False)
    assert fred["H4"]["reason"] == "Nguồn chỉ có giá ngày" and fred["D1"]["macd"] is not None


def test_a_vietnamese_row_needs_prices_of_the_session_itself():
    stale = build_cells(daily(1200, end=date(2026, 10, 22)), hourly(400, end=date(2026, 10, 22)), session_date=date(2026, 10, 23),
                        hourly_supported=True)
    assert stale["D1"]["reason"] == "Chưa có giá của phiên" and stale["H1"]["reason"] == "Chưa có giá của phiên"


def test_compare_marks_macd_and_rsi_zone_changes():
    cur = {"groups": [{"rows": [{"id": "FPT", "cells": {"D1": {"macd": "up,>0", "rsi": 72, "zone": "overbought", "reason": None}}}]}]}
    prev = {"session_date": "2026-10-22",
            "groups": [{"rows": [{"id": "FPT", "cells": {"D1": {"macd": "down,<0", "rsi": 65, "zone": "neutral", "reason": None}}}]}]}
    out = compare(cur, prev)
    c = out["groups"][0]["rows"][0]["cells"]["D1"]
    assert (c["macd_changed"], c["previous_macd"], c["rsi_changed"], c["previous_zone"]) == (True, "down,<0", True, "neutral")
    assert out["previous_date"] == "2026-10-22"
    first = compare(cur, None)["groups"][0]["rows"][0]["cells"]["D1"]
    assert first["macd_changed"] is False and compare(cur, None)["previous_date"] is None


def test_snapshot_store_saves_finds_the_previous_session_and_prunes(tmp_path):
    s = SnapshotStore(tmp_path / "trend")
    for d in ("2026-07-01", "2026-10-22", "2026-10-23"):
        s.save({"session_date": d, "groups": []})
    assert s.latest()["session_date"] == "2026-10-23" and s.before(date(2026, 10, 23))["session_date"] == "2026-10-22"
    s.prune(date(2026, 10, 23), keep_days=90)
    assert sorted(p.stem for p in (tmp_path / "trend").glob("*.json")) == ["2026-10-22", "2026-10-23"]


class FakeVn:
    def __init__(self):
        self.calls = []

    def fetch_closes(self, symbol, start, end, *, interval, index):
        self.calls.append((symbol, interval, start))
        if interval == "1D":
            return [(t, str(v)) for t, v in daily(1200, end=end)]
        return [(t, str(v)) for t, v in hourly(400, end=end)]


def fake_get(url):
    if "coinbase" in url:
        if "BTC" in url:
            raise OSError("offline")
        g = int(url.split("granularity=")[1].split("&")[0])
        start = datetime.fromisoformat(url.split("start=")[1].split("&")[0].replace("Z", "+00:00"))
        return json.dumps([[int((start + timedelta(seconds=g * i)).timestamp()), 1, 2, 1, str(100 + i), 1] for i in range(300)])
    return "observation_date,X\n" + "\n".join(f"{d.date()},{v}" for d, v in daily(1200))


def test_run_builds_saves_and_reports_source_errors(tmp_path):
    now = datetime(2026, 10, 23, 15, 35, tzinfo=VN)
    vn = FakeVn()
    result = run_trend(tmp_path, CAL, now=now, provider=vn, get=fake_get, pause=0)
    assert result["status"] == "ok" and result["errors"] == {"BTC": "error:OSError"}
    snap = SnapshotStore(tmp_path / "trend").latest()
    rows = {r["id"]: r for g in snap["groups"] for r in g["rows"]}
    assert rows["FPT"]["cells"]["D1"]["macd"] == "up,>0" and rows["BTC"]["cells"]["D1"]["reason"] == "Lỗi nguồn"
    assert rows["VN10Y"]["cells"]["M"]["reason"] == "Không có nguồn miễn phí hợp lệ" and rows["US10Y"]["cells"]["H1"]["reason"] == "Nguồn chỉ có giá ngày"
    assert ("FPT", "1D", date(2026, 10, 23) - timedelta(days=2920)) in vn.calls  # first run backfills the full window
    run_trend(tmp_path, CAL, now=now + timedelta(hours=2), provider=vn, get=fake_get, pause=0)
    assert ("FPT", "1D", date(2026, 10, 23) - timedelta(days=60)) in vn.calls  # later runs only refresh


def test_run_skips_outside_sessions_and_before_15_30(tmp_path):
    assert run_trend(tmp_path, CAL, now=datetime(2026, 10, 24, 16, tzinfo=VN), provider=FakeVn(), get=fake_get)["reason"] == "not_a_session"
    assert run_trend(tmp_path, CAL, now=datetime(2026, 10, 23, 15, 29, tzinfo=VN), provider=FakeVn(), get=fake_get)["reason"] == "before_close"


def test_cli_trend_run_prints_a_summary(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("investment_agent.market.trend.time_module.sleep", lambda seconds: None)
    from investment_agent.cli import trend_run
    cal_path = tmp_path / "cal.json"
    cal_path.write_text(json.dumps({"version": "x", "source": "HOSE notice", "holidays": [], "first": "2016-01-01", "last": "2026-12-31"}),
                        encoding="utf-8")
    code = trend_run(tmp_path, cal_path, now=datetime(2026, 10, 23, 15, 35, tzinfo=VN), provider=FakeVn(), get=fake_get)
    assert code == 1 and '"BTC": "error:OSError"' in capsys.readouterr().out  # 1: a source failed, the board was still saved


def test_a_short_macd_history_is_explained_even_when_rsi_has_a_value():
    from investment_agent.market.trend import _cell
    c = _cell([100.0 * 1.01 ** i for i in range(20)])  # 20 bars: enough for RSI 14, not for MACD 12-26-9
    assert c["macd"] is None and c["rsi"] is not None and c["reason"] == "Chưa đủ lịch sử"


class FlakyVn(FakeVn):
    """Fails the first call for each symbol, as Vnstock did for MWG and FPT on the live trial."""
    def __init__(self):
        super().__init__()
        self.failed = set()

    def fetch_closes(self, symbol, start, end, *, interval, index):
        if symbol not in self.failed:
            self.failed.add(symbol)
            raise ConnectionError("transient")
        return super().fetch_closes(symbol, start, end, interval=interval, index=index)


def test_a_transient_source_error_is_retried_once(tmp_path):
    result = run_trend(tmp_path, CAL, now=datetime(2026, 10, 23, 15, 35, tzinfo=VN), provider=FlakyVn(), get=fake_get, pause=0)
    assert "FPT" not in result["errors"] and result["errors"] == {"BTC": "error:OSError"}
