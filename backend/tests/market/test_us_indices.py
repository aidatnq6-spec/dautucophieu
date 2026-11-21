"""Chứng khoán Mỹ on Vĩ mô (owner, 21/11/2026): S&P 500, Nasdaq Composite and Dow Jones from FRED's daily series, each with its own
session date, the session's change and the change over 30 days. FRED marks a holiday with "." (skipped, never filled)."""

from datetime import date

from investment_agent.market.leading import MacroStore
from investment_agent.market.us_indices import INDICES, fetch_us_indices, us_indices

CSV = {"SP500": "observation_date,SP500\n2026-10-20,6000.00\n2026-11-18,6100.00\n2026-11-19,.\n2026-11-20,6200.00\n",
       "NASDAQCOM": "observation_date,NASDAQCOM\n2026-10-20,20000\n2026-11-20,21000\n",
       "DJIA": "observation_date,DJIA\n2026-11-20,48000\n"}


def get(url):
    return next(text for code, text in CSV.items() if f"id={code}" in url)


def test_the_three_series_are_stored_from_fred(tmp_path):
    store = MacroStore(tmp_path)
    assert fetch_us_indices(store, get=get, sleep=lambda s: None) == {"us_sp500": "ok", "us_nasdaq": "ok", "us_dow": "ok"}
    assert [p["date"] for p in store.read("us_sp500")] == ["2026-10-20", "2026-11-18", "2026-11-20"]  # the holiday "." skipped
    assert [k for k, _, _ in INDICES] == ["us_sp500", "us_nasdaq", "us_dow"]


def test_each_index_has_its_session_date_its_day_and_30_day_change(tmp_path):
    store = MacroStore(tmp_path)
    fetch_us_indices(store, get=get, sleep=lambda s: None)
    rows = {r["id"]: r for r in us_indices(store, today=date(2026, 11, 21))["rows"]}
    sp = rows["us_sp500"]
    assert sp["name"] == "S&P 500" and sp["close"] == "6200" and sp["date"] == "2026-11-20" and sp["stale"] is False
    assert sp["day_pct"] == "0.0164" and sp["m1_pct"] == "0.0333"  # 6200 / 6100 − 1 ; 6200 / 6000 − 1 (last close on or before 21/10)
    assert rows["us_dow"]["day_pct"] is None and rows["us_dow"]["m1_pct"] is None  # one close only: nothing to compare


def test_a_failed_read_says_so_and_an_old_figure_is_marked(tmp_path):
    store = MacroStore(tmp_path)

    def broken(url):
        raise OSError("down")
    out = fetch_us_indices(store, get=broken, sleep=lambda s: None)
    assert out["us_sp500"].startswith("error:")
    fetch_us_indices(store, get=get, sleep=lambda s: None)
    assert us_indices(store, today=date(2026, 12, 5))["rows"][0]["stale"] is True  # 15 days after its last session
    assert us_indices(MacroStore(tmp_path / "none"), today=date(2026, 11, 21))["rows"] == []


def test_macro_sync_reads_them_and_a_failure_inside_seven_days_is_late_not_stale(tmp_path):
    from datetime import datetime, timedelta
    from investment_agent.cli import _macro_late
    from investment_agent.market.leading import VN
    today = datetime.now(VN).date()
    MacroStore(tmp_path).upsert("us_sp500", [(today - timedelta(days=2), "6200")], entry="auto")
    late, stale = _macro_late(tmp_path, {"us_sp500": "error:ServerError", "us_dow": "error:ServerError"}, [])
    assert late == ["us_sp500"] and stale == ["us_dow"]  # nothing stored for the Dow: stale


def test_the_extras_of_macro_sync_include_the_us_indices():
    import inspect
    from investment_agent import cli
    assert "fetch_us_indices" in inspect.getsource(cli._macro_extras)