import json
from datetime import date, timedelta
from decimal import Decimal

from investment_agent.market.calendar import TradingCalendar
from investment_agent.market.prices import PriceBar, PriceStore, ingest
from investment_agent.market.view import EmptyMarket, PricePoint, StoreMarket, SyntheticMarket
from investment_agent.market.watchlist import load_watchlist, watchlist_rows

CAL = TradingCalendar(version="t", source="test", holidays=frozenset(), first=date(2026, 1, 1), last=date(2026, 12, 31))


def closes(*values, end=date(2026, 10, 23)):
    days = list(reversed(CAL.sessions(end - timedelta(days=60), end)))[:len(values)]
    return [PricePoint(Decimal(v), d) for v, d in zip(values, reversed(days))]


def test_load_reads_symbols_and_optional_groups(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("mbb\n\nFPT\nMBB\n", encoding="utf-8")
    assert load_watchlist(tmp_path).symbols == ("MBB", "FPT")
    assert load_watchlist(tmp_path).groups == {}
    (tmp_path / "index-groups.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "vnstock:kbs",
                                                            "groups": {"VN30": ["FPT"], "VN100": ["FPT", "MBB"]}}), encoding="utf-8")
    wl = load_watchlist(tmp_path)
    assert wl.groups == {"VN30": ("FPT",), "VN100": ("FPT", "MBB")} and wl.groups_as_of == "2026-10-25"


def test_missing_files_give_an_empty_watchlist(tmp_path):
    assert load_watchlist(tmp_path).symbols == () and load_watchlist(None).symbols == ()


def test_rows_report_session_and_twenty_session_changes(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nVCB\n", encoding="utf-8")
    (tmp_path / "index-groups.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "groups": {"VN30": ["FPT", "VCB"]}}), encoding="utf-8")
    fpt = closes(*([50_000] * 20 + [55_000, 57_000]))  # 22 sessions: 20 sessions ago 50,000; yesterday 55,000
    market = SyntheticMarket(prices={"FPT": fpt[-1]}, history={"FPT": fpt})
    rows = watchlist_rows(market, load_watchlist(tmp_path), held={"VCB"})
    assert rows[0] == {"ticker": "FPT", "groups": ["VN30"], "held": False, "close": "57000", "date": "2026-10-23",
                       "change_1d": "0.0364", "change_20d": "0.1400", "stale": False}
    assert rows[1] == {"ticker": "VCB", "groups": ["VN30"], "held": True, "close": None, "date": None,
                       "change_1d": None, "change_20d": None, "stale": False}


def test_short_history_has_no_twenty_session_change(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    fpt = closes(56_000, 57_000)
    row = watchlist_rows(SyntheticMarket(prices={"FPT": fpt[-1]}, history={"FPT": fpt}), load_watchlist(tmp_path), held=set())[0]
    assert (row["change_1d"], row["change_20d"]) == ("0.0179", None)


def test_store_market_history_and_stale_flag(tmp_path):
    store = PriceStore(tmp_path)
    bars = [PriceBar(entity_id="FPT", session_date=d, open="1", high="60000", low="1", close=str(50_000 + i * 100),
                     volume=1, currency="VND", source_id="t", observed_at="2026-10-23T10:00:00Z", provenance_mode="latest_restated",
                     price_basis="adjusted") for i, d in enumerate(CAL.sessions(date(2026, 10, 1), date(2026, 10, 23)))]
    ingest(store, CAL, bars, revision_id="r1")
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    fresh = StoreMarket(store, CAL, today=lambda: date(2026, 10, 25))
    assert [p.session_date for p in fresh.recent_closes("FPT", 2)] == [date(2026, 10, 22), date(2026, 10, 23)]
    old = StoreMarket(store, CAL, today=lambda: date(2026, 11, 20), max_age_days=10)
    row = watchlist_rows(old, load_watchlist(tmp_path), held=set())[0]
    assert row["close"] == "51600" and row["stale"] is True  # shown with its date, flagged as old


def test_empty_market_rows_have_no_prices(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    assert watchlist_rows(EmptyMarket(), load_watchlist(tmp_path), held=set())[0]["close"] is None
