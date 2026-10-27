from datetime import date, datetime, timedelta

from investment_agent.market.history import backfill_history, history_complete
from investment_agent.market.series import SeriesStore


def fake_source(first: date, last: date, window_rows: int = 3):
    """Daily closes from `first` to `last`, served at most `window_rows` at a time from the end of the window (like Vnstock)."""
    calls = []

    def fetch(start: date, end: date):
        calls.append((start, end))
        days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
        rows = [d for d in days if start <= d <= end][-window_rows:]
        return [(datetime(d.year, d.month, d.day), "10") for d in rows]
    return fetch, calls


def test_history_is_filled_backwards_until_the_source_has_nothing_older(tmp_path):
    store = SeriesStore(tmp_path)
    store.upsert("KDH-1d", [(datetime(2020, 1, 10), "10")])
    fetch, calls = fake_source(date(2020, 1, 2), date(2020, 1, 10))
    added = backfill_history(store, "KDH-1d", fetch, root=tmp_path)
    assert [p[0].date() for p in store.read("KDH-1d")][:2] == [date(2020, 1, 2), date(2020, 1, 3)] and added == 8
    assert history_complete(tmp_path, "KDH-1d")
    assert calls[0][1] == date(2020, 1, 9)  # each window ends the day before the oldest stored close


def test_a_completed_series_is_not_fetched_again(tmp_path):
    store = SeriesStore(tmp_path)
    store.upsert("KDH-1d", [(datetime(2020, 1, 10), "10")])
    fetch, calls = fake_source(date(2020, 1, 9), date(2020, 1, 10))
    backfill_history(store, "KDH-1d", fetch, root=tmp_path)
    n = len(calls)
    assert backfill_history(store, "KDH-1d", fetch, root=tmp_path) == 0 and len(calls) == n


def test_a_failed_window_leaves_the_series_unfinished_for_the_next_run(tmp_path):
    store = SeriesStore(tmp_path)
    store.upsert("KDH-1d", [(datetime(2020, 1, 10), "10")])

    def broken(start, end):
        raise OSError("offline")
    try:
        backfill_history(store, "KDH-1d", broken, root=tmp_path)
    except OSError:
        pass
    assert not history_complete(tmp_path, "KDH-1d") and len(store.read("KDH-1d")) == 1
