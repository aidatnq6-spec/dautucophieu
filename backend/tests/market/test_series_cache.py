import os
from datetime import datetime

from investment_agent.market.series import SeriesStore


def test_a_series_is_read_again_from_disk_once_the_file_changes(tmp_path):
    store = SeriesStore(tmp_path)
    store.upsert("FPT-1d", [(datetime(2026, 11, 13), "50")])
    assert store.read("FPT-1d") == [(datetime(2026, 11, 13), 50.0)] and store.points("FPT-1d") == [("2026-11-13", "50")]
    first = store.read("FPT-1d")
    first.append("changed by a caller")
    assert store.read("FPT-1d") == [(datetime(2026, 11, 13), 50.0)]  # a caller's change does not reach the next reader
    store.upsert("FPT-1d", [(datetime(2026, 11, 14), "51")])
    assert store.read("FPT-1d")[-1] == (datetime(2026, 11, 14), 51.0)


def test_a_file_replaced_with_the_same_size_and_time_is_not_the_case_we_rely_on_but_a_new_time_is_read(tmp_path):
    store = SeriesStore(tmp_path)
    store.upsert("X-1d", [(datetime(2026, 1, 1), "10")])
    path = tmp_path / "X-1d.json"
    path.write_text(path.read_text(encoding="utf-8").replace('"10"', '"11"'), encoding="utf-8")
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
    assert store.read("X-1d") == [(datetime(2026, 1, 1), 11.0)]
    assert store.read("NONE-1d") == [] and store.points("NONE-1d") == []
