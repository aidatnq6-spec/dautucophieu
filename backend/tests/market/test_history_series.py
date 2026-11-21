"""Lịch sử vĩ mô dài (owner, 21/11/2026): Vietnam's monthly CPI, industrial production, USD/VND and merchandise exports from the
World Bank's Global Economic Monitor (2010 on; open API, robots.txt 404), and the US 10-year yield's full daily history from FRED.
Read once a week, for Thống kê lịch sử. A month without a figure stays out (null), never filled."""

import json
from datetime import date

from investment_agent.market.history_series import GEM_SERIES, fetch_history_series, parse_gem
from investment_agent.market.leading import MacroStore

GEM = json.dumps([{"page": 1, "pages": 1}, [
    {"date": "2026M08", "value": None}, {"date": "2026M07", "value": 4.47703214529}, {"date": "2026M06", "value": 3.9}]])
FRED = "observation_date,DGS10\n1962-01-02,4.06\n1962-01-03,.\n2026-11-20,4.12\n"


def get(url):
    return FRED if "fred" in url else GEM


def test_a_gem_month_is_dated_at_its_end_and_a_null_month_left_out():
    assert parse_gem(GEM) == [(date(2026, 6, 30), "3.9"), (date(2026, 7, 31), "4.47703214529")]


def test_the_series_are_stored_once_a_week(tmp_path):
    store, calls = MacroStore(tmp_path), []

    def counting(url):
        calls.append(url)
        return get(url)
    out = fetch_history_series(store, tmp_path, get=counting, sleep=lambda s: None, today=date(2026, 11, 21))
    assert out == {**{k: "ok" for k, _, _ in GEM_SERIES}, "us10y_long": "ok"}
    assert store.read("wb_vn_cpi_yoy")[-1] == {**store.read("wb_vn_cpi_yoy")[-1], "date": "2026-07-31", "value": "4.47703214529"}
    assert [o["date"] for o in store.read("us10y_long")] == ["1962-01-02", "2026-11-20"]
    n = len(calls)
    assert fetch_history_series(store, tmp_path, get=counting, sleep=lambda s: None, today=date(2026, 11, 25)) == {} and len(calls) == n
    assert fetch_history_series(store, tmp_path, get=counting, sleep=lambda s: None, today=date(2026, 11, 28)) != {}  # a week later


def test_a_failure_is_said_and_tried_again_next_run(tmp_path):
    store = MacroStore(tmp_path)

    def broken(url):
        raise OSError("down")
    out = fetch_history_series(store, tmp_path, get=broken, sleep=lambda s: None, today=date(2026, 11, 21))
    assert all(v.startswith("error:") for v in out.values())
    assert fetch_history_series(store, tmp_path, get=get, sleep=lambda s: None, today=date(2026, 11, 21))["wb_vn_cpi_yoy"] == "ok"


def test_macro_sync_reads_them_and_a_failure_within_their_age_is_late():
    import inspect
    from datetime import datetime, timedelta

    from investment_agent import cli
    from investment_agent.market.leading import VN
    assert "fetch_history_series" in inspect.getsource(cli._macro_extras)
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp())
    MacroStore(tmp).upsert("wb_vn_cpi_yoy", [(datetime.now(VN).date() - timedelta(days=120), "4.5")], entry="auto")  # four months behind: normal
    late, stale = cli._macro_late(tmp, {"wb_vn_cpi_yoy": "error:ServerError", "us10y_long": "error:ServerError"}, [])
    assert late == ["wb_vn_cpi_yoy"] and stale == ["us10y_long"]