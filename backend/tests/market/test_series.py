from datetime import datetime, timedelta, timezone

import pytest

from investment_agent.market.series import SeriesStore

VN = timezone(timedelta(hours=7))


def test_upsert_merges_by_timestamp_and_reads_back_sorted(tmp_path):
    s = SeriesStore(tmp_path / "intraday")
    s.upsert("FPT-1h", [(datetime(2026, 10, 23, 10, tzinfo=VN), "57.1"), (datetime(2026, 10, 23, 9, tzinfo=VN), "57.0")])
    s.upsert("FPT-1h", [(datetime(2026, 10, 23, 10, tzinfo=VN), "57.2")])
    assert s.read("FPT-1h") == [(datetime(2026, 10, 23, 9, tzinfo=VN), 57.0), (datetime(2026, 10, 23, 10, tzinfo=VN), 57.2)]


def test_daily_keys_keep_dates_and_old_points_beyond_the_cap_are_dropped(tmp_path):
    s = SeriesStore(tmp_path)
    s.upsert("BTC-1d", [(datetime(2026, 10, d), str(d)) for d in range(1, 11)], keep=3)
    assert [t.day for t, _ in s.read("BTC-1d")] == [8, 9, 10]


def test_missing_key_reads_empty_and_bad_keys_are_refused(tmp_path):
    s = SeriesStore(tmp_path)
    assert s.read("NONE-1d") == []
    with pytest.raises(ValueError):
        s.upsert("../x", [])
