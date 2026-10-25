from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from investment_agent.market.calendar import TradingCalendar
from investment_agent.market.prices import (
    AdjustmentFactor, PriceBar, PriceError, PriceStore, adjusted_closes, ingest, session_series,
)
from investment_agent.market.security_master import MasterError, SecurityMaster, TickerMapping

OBSERVED = datetime(2026, 10, 24, 10, tzinfo=timezone.utc)
CAL = TradingCalendar(version="cal-test", source="synthetic", holidays=frozenset({date(2026, 9, 2)}), first=date(2026, 8, 3), last=date(2026, 12, 31))


def bar(day, price, entity="ent-fpt", **changes):
    data = {"entity_id": entity, "session_date": day, "open": str(price), "high": str(price + 100), "low": str(price - 100),
            "close": str(price), "volume": 1000, "currency": "VND", "source_id": "fixture", "observed_at": OBSERVED.isoformat(),
            "provenance_mode": "synthetic"}
    data.update(changes)
    return PriceBar.model_validate(data)


def test_calendar_skips_weekends_and_holidays():
    sessions = CAL.sessions(date(2026, 8, 31), date(2026, 9, 7))
    assert sessions == (date(2026, 8, 31), date(2026, 9, 1), date(2026, 9, 3), date(2026, 9, 4), date(2026, 9, 7))


def test_calendar_rejects_dates_outside_its_known_range():
    with pytest.raises(ValueError):
        CAL.sessions(date(2026, 7, 1), date(2026, 8, 5))


def test_bar_on_holiday_or_weekend_is_rejected(tmp_path):
    store = PriceStore(tmp_path)
    for day in ("2026-09-02", "2026-09-05"):
        with pytest.raises(PriceError) as error:
            ingest(store, CAL, [bar(day, 20_000)], revision_id="r1")
        assert error.value.code == "non_session_bar"


@pytest.mark.parametrize("changes, code", [
    ({"currency": "USD"}, "currency"), ({"high": "19000"}, "ohlc_inconsistent"), ({"low": "21000"}, "ohlc_inconsistent"),
    ({"close": "0", "open": "0", "low": "0", "high": "0"}, "non_positive_price"),
])
def test_quality_checks_before_publish(tmp_path, changes, code):
    with pytest.raises(PriceError) as error:
        ingest(PriceStore(tmp_path), CAL, [bar("2026-09-01", 20_000, **changes)], revision_id="r1")
    assert error.value.code == code


def test_naive_observation_time_rejected():
    with pytest.raises(ValueError):
        bar("2026-09-01", 20_000, observed_at="2026-10-24T10:00:00")


def test_suspended_or_missing_sessions_are_not_forward_filled(tmp_path):
    store = PriceStore(tmp_path)
    ingest(store, CAL, [bar("2026-09-01", 20_000), bar("2026-09-04", 21_000)], revision_id="r1")
    rows = session_series(store, CAL, "ent-fpt", date(2026, 9, 1), date(2026, 9, 4), suspended={date(2026, 9, 3)})
    assert [(r.session_date, r.close, r.status) for r in rows] == [
        (date(2026, 9, 1), Decimal(20_000), "traded"), (date(2026, 9, 3), None, "suspended"), (date(2026, 9, 4), Decimal(21_000), "traded")]
    assert date(2026, 9, 2) not in [r.session_date for r in rows]


def test_missing_session_without_suspension_is_marked_missing(tmp_path):
    store = PriceStore(tmp_path)
    ingest(store, CAL, [bar("2026-09-01", 20_000)], revision_id="r1")
    rows = session_series(store, CAL, "ent-fpt", date(2026, 9, 1), date(2026, 9, 3))
    assert rows[-1].status == "missing" and rows[-1].close is None


def test_retry_of_same_revision_does_not_duplicate(tmp_path):
    store = PriceStore(tmp_path)
    bars = [bar("2026-09-01", 20_000), bar("2026-09-03", 20_500)]
    first = ingest(store, CAL, bars, revision_id="r1")
    again = ingest(store, CAL, bars, revision_id="r1")
    assert again == first and len(store.revisions("ent-fpt")) == 1
    assert len(session_series(store, CAL, "ent-fpt", date(2026, 9, 1), date(2026, 9, 3))) == 2


def test_same_revision_id_with_different_content_is_rejected(tmp_path):
    store = PriceStore(tmp_path)
    ingest(store, CAL, [bar("2026-09-01", 20_000)], revision_id="r1")
    with pytest.raises(PriceError) as error:
        ingest(store, CAL, [bar("2026-09-01", 20_100)], revision_id="r1")
    assert error.value.code == "revision_conflict"


def test_lookback_correction_creates_revision_and_keeps_old(tmp_path):
    store = PriceStore(tmp_path)
    ingest(store, CAL, [bar("2026-09-01", 20_000), bar("2026-09-03", 20_500)], revision_id="r1")
    ingest(store, CAL, [bar("2026-09-03", 20_600), bar("2026-09-04", 21_000)], revision_id="r2")
    latest = session_series(store, CAL, "ent-fpt", date(2026, 9, 1), date(2026, 9, 4))
    assert [r.close for r in latest] == [Decimal(20_000), Decimal(20_600), Decimal(21_000)]
    assert [r.revision_id for r in latest] == ["r1", "r2", "r2"]
    as_first = session_series(store, CAL, "ent-fpt", date(2026, 9, 1), date(2026, 9, 4), revision="r1")
    assert as_first[1].close == Decimal(20_500) and as_first[2].status == "missing"


def test_mixed_entities_in_one_batch_partition_per_entity(tmp_path):
    store = PriceStore(tmp_path)
    ingest(store, CAL, [bar("2026-09-01", 20_000), bar("2026-09-01", 70_000, entity="ent-vnm")], revision_id="r1")
    assert {p.parent.name for p in tmp_path.rglob("*.parquet")} == {"ent-fpt", "ent-vnm"}
    assert not list(tmp_path.rglob("*.tmp"))


def test_failed_write_leaves_previous_revision_readable(tmp_path, monkeypatch):
    store = PriceStore(tmp_path)
    ingest(store, CAL, [bar("2026-09-01", 20_000)], revision_id="r1")
    monkeypatch.setattr("investment_agent.market.prices.os.replace", lambda *a: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        ingest(store, CAL, [bar("2026-09-03", 20_500)], revision_id="r2")
    monkeypatch.undo()
    assert store.revisions("ent-fpt") == ("r1",)
    assert session_series(store, CAL, "ent-fpt", date(2026, 9, 1), date(2026, 9, 1))[0].close == Decimal(20_000)


def test_raw_prices_stay_raw_and_adjustment_factors_apply_before_ex_date(tmp_path):
    store = PriceStore(tmp_path)
    ingest(store, CAL, [bar("2026-09-01", 30_000), bar("2026-09-03", 15_100), bar("2026-09-04", 15_200)], revision_id="r1")
    split = AdjustmentFactor(entity_id="ent-fpt", action_id="split-2026", ex_date="2026-09-03", factor="0.5", kind="split", source_id="fixture")
    rows = session_series(store, CAL, "ent-fpt", date(2026, 9, 1), date(2026, 9, 4))
    assert rows[0].close == Decimal(30_000)  # raw unchanged
    assert [a.adjusted_close for a in adjusted_closes(rows, [split])] == [Decimal(15_000), Decimal(15_100), Decimal(15_200)]


def test_adjustment_factor_must_be_positive_and_at_most_one_per_action():
    with pytest.raises(ValueError):
        AdjustmentFactor(entity_id="e", action_id="a", ex_date="2026-09-03", factor="0", kind="split", source_id="s")


# --- security master ---------------------------------------------------------

def test_exchange_transfer_keeps_same_issuer():
    master = SecurityMaster([
        TickerMapping(entity_id="ent-abc", ticker="ABC", exchange="HNX", valid_from="2010-01-04", valid_to="2018-06-30"),
        TickerMapping(entity_id="ent-abc", ticker="ABC", exchange="HOSE", valid_from="2018-07-02", valid_to=None)])
    assert master.resolve("ABC", date(2015, 1, 5)) == master.resolve("ABC", date(2020, 1, 6)) == "ent-abc"
    assert master.exchange_on("ent-abc", date(2015, 1, 5)) == "HNX"
    assert master.exchange_on("ent-abc", date(2020, 1, 6)) == "HOSE"


def test_reused_ticker_by_different_issuer_is_not_joined():
    master = SecurityMaster([
        TickerMapping(entity_id="ent-old", ticker="XYZ", exchange="HOSE", valid_from="2008-01-02", valid_to="2014-12-31"),
        TickerMapping(entity_id="ent-new", ticker="XYZ", exchange="HOSE", valid_from="2019-01-02", valid_to=None)])
    assert master.resolve("XYZ", date(2010, 1, 4)) == "ent-old"
    assert master.resolve("XYZ", date(2020, 1, 6)) == "ent-new"
    with pytest.raises(MasterError):
        master.resolve("XYZ", date(2016, 1, 4))


def test_overlapping_ticker_mappings_rejected():
    with pytest.raises(MasterError):
        SecurityMaster([
            TickerMapping(entity_id="ent-a", ticker="DUP", exchange="HOSE", valid_from="2010-01-04", valid_to=None),
            TickerMapping(entity_id="ent-b", ticker="DUP", exchange="HOSE", valid_from="2015-01-05", valid_to=None)])


def test_batched_history_load_with_checkpoint_and_rate_limit(tmp_path):
    from investment_agent.market.prices import load_history

    calls, sleeps = [], []

    def fetch(entity_id, start, end):
        calls.append((start, end))
        return [bar(d.isoformat(), 20_000) for d in CAL.sessions(start, end)]

    store = PriceStore(tmp_path)
    checkpoint = tmp_path / "checkpoint.json"
    load_history(store, CAL, fetch, "ent-fpt", date(2026, 8, 3), date(2026, 9, 30), batch_sessions=10, checkpoint=checkpoint,
                 sleep=sleeps.append, min_interval=0.5, revision_prefix="hist")
    batches = -(-len(CAL.sessions(date(2026, 8, 3), date(2026, 9, 30))) // 10)
    assert len(calls) == batches == 5 and len(sleeps) == batches - 1
    calls.clear()
    load_history(store, CAL, fetch, "ent-fpt", date(2026, 8, 3), date(2026, 9, 30), batch_sessions=10, checkpoint=checkpoint,
                 sleep=sleeps.append, min_interval=0.5, revision_prefix="hist")
    assert calls == []  # resumed from checkpoint
    assert len(session_series(store, CAL, "ent-fpt", date(2026, 8, 3), date(2026, 9, 30))) == len(CAL.sessions(date(2026, 8, 3), date(2026, 9, 30)))
