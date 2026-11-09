import os
from datetime import date, datetime, timezone

import pytest

from investment_agent.market.prices import PriceBar, PriceError, PriceStore


def bar(day: date, close: str) -> PriceBar:
    return PriceBar(entity_id="AAA", session_date=day, open=close, high=close, low=close, close=close, volume=100, currency="VND",
                    source_id="test:src", observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc), provenance_mode="synthetic")


def counting(store, monkeypatch):
    calls = []
    real = store.read_revision
    monkeypatch.setattr(store, "read_revision", lambda entity, entry: (calls.append(entry["revision_id"]), real(entity, entry))[1])
    return calls


def test_the_second_look_at_a_ticker_does_not_read_its_files_again(tmp_path, monkeypatch):
    store = PriceStore(tmp_path)
    store.write_revision("AAA", "r1", [bar(date(2026, 1, 5), "10")])
    calls = counting(store, monkeypatch)
    first = store.latest("AAA")
    first.clear()  # what one caller does to its copy reaches no other
    assert calls == ["r1"] and store.latest("AAA")[date(2026, 1, 5)][0].close == 10 and calls == ["r1"]


def test_a_new_revision_is_seen_at_once(tmp_path):
    store = PriceStore(tmp_path)
    store.write_revision("AAA", "r1", [bar(date(2026, 1, 5), "10")])
    assert set(store.latest("AAA")) == {date(2026, 1, 5)}
    store.write_revision("AAA", "r2", [bar(date(2026, 1, 6), "11")])
    assert set(store.latest("AAA")) == {date(2026, 1, 5), date(2026, 1, 6)}


def test_a_revision_limit_gets_its_own_answer(tmp_path):
    store = PriceStore(tmp_path)
    store.write_revision("AAA", "r1", [bar(date(2026, 1, 5), "10")])
    store.write_revision("AAA", "r2", [bar(date(2026, 1, 6), "11")])
    assert len(store.latest("AAA")) == 2 and len(store.latest("AAA", revision="r1")) == 1 and len(store.latest("AAA")) == 2


def test_a_file_altered_after_the_first_look_is_still_caught_by_its_checksum(tmp_path):
    store = PriceStore(tmp_path)
    store.write_revision("AAA", "r1", [bar(date(2026, 1, 5), "10")])
    store.write_revision("AAA", "r2", [bar(date(2026, 1, 6), "11")])
    store.latest("AAA")
    folder = tmp_path / "prices" / "AAA"
    (folder / "r1.parquet").write_bytes((folder / "r2.parquet").read_bytes())
    os.utime(folder / "r1.parquet", (1, 1))
    with pytest.raises(PriceError):
        store.latest("AAA")
