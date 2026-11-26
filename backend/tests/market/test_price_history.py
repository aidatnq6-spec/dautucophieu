"""Giá dài hạn đã điều chỉnh: VNDirect's adjusted daily closes since 2013 for every HOSE ticker, refreshed whole once a week."""

import json
from datetime import datetime, timezone

from investment_agent.market.price_history import PriceHistoryStore, parse_closes, sync_price_history

NOW = datetime(2026, 11, 26, 13, tzinfo=timezone.utc)


def rows(symbol, pairs):
    return json.dumps({"data": [{"code": symbol, "date": d, "adClose": c} for d, c in pairs]})


def test_closes_are_sorted_one_per_day_and_bad_rows_are_dropped_not_repaired():
    text = json.dumps({"data": [{"code": "KDH", "date": "2024-10-17", "adClose": 27.563}, {"code": "KDH", "date": "2013-01-02", "adClose": 1.931},
                                {"code": "KDH", "date": "2014-05-05", "adClose": None}, {"code": "KDH", "date": "2014-05-06", "adClose": 0},
                                {"code": "XYZ", "date": "2015-01-05", "adClose": 9.0}]})
    assert parse_closes(text, symbol="KDH") == [["2013-01-02", "1.931"], ["2024-10-17", "27.563"]]


def _listing(tmp_path, symbols):
    (tmp_path / "hose-listing.json").write_text(json.dumps({"at": "x", "listing": {"symbols": symbols}}), encoding="utf-8")


def test_every_hose_ticker_missing_or_older_than_a_week_is_fetched_oldest_first_up_to_the_limit(tmp_path):
    _listing(tmp_path, ["AAA", "BBB", "CCC", "DDD"])
    store = PriceHistoryStore(tmp_path)
    store.save("BBB", {"symbol": "BBB", "fetched_at": "2026-11-25T00:00:00+00:00", "closes": []})  # fresh: skipped
    store.save("CCC", {"symbol": "CCC", "fetched_at": "2026-11-01T00:00:00+00:00", "closes": []})  # stale
    asked, urls = [], []

    def get(url):
        symbol = url.split("code:")[1].split("~")[0]
        asked.append(symbol)
        urls.append(url)
        return rows(symbol, [("2026-11-25", 10.5)])

    out = sync_price_history(tmp_path, get=get, now=NOW, limit=2, sleep=lambda s: None)
    assert asked == ["AAA", "DDD"]  # never fetched first, then the stalest; the limit stops before CCC
    assert out["status"] == "ok" and out["updated"] == 2 and out["due"] == 3
    saved = store.read("AAA")
    assert saved == {"symbol": "AAA", "fetched_at": NOW.isoformat(), "source": "vndirect:finfo", "adjusted": True, "unit": "nghìn đồng",
                     "closes": [["2026-11-25", "10.5"]]}
    assert all("date:gte:2013-01-01" in u and "adClose" in u for u in urls)  # the whole adjusted series, every time


def test_named_tickers_are_fetched_however_recent_and_an_empty_answer_keeps_what_was_stored(tmp_path):
    _listing(tmp_path, [])
    store = PriceHistoryStore(tmp_path)
    store.save("KDH", {"symbol": "KDH", "fetched_at": NOW.isoformat(), "closes": [["2013-01-02", "1.931"]]})

    def get(url):
        if "code:FPT" in url:
            raise OSError("timeout")
        return json.dumps({"data": []})

    out = sync_price_history(tmp_path, get=get, now=NOW, symbols=["KDH", "FPT"], sleep=lambda s: None)
    assert out["status"] == "partial" and out["updated"] == 0 and out["empty"] == 1 and out["failed"] == {"FPT": "OSError"}
    assert store.read("KDH")["closes"] == [["2013-01-02", "1.931"]]


def test_the_store_refuses_a_bad_ticker(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        PriceHistoryStore(tmp_path).read("../x")


def test_vnindex_sessions_since_2013_are_kept_as_a_list_of_days(tmp_path):
    from investment_agent.market.price_history import INDEX_SESSIONS_URL, read_index_sessions, sync_index_sessions
    asked = []

    def get(url):
        asked.append(url)
        return json.dumps({"data": [{"code": "VNINDEX", "date": "2013-01-03", "close": 1}, {"code": "VNINDEX", "date": "2013-01-02", "close": 1},
                                    {"code": "VN30", "date": "2013-01-04", "close": 1}, {"code": "VNINDEX", "date": "2013-01-07", "close": None}]})
    assert sync_index_sessions(tmp_path, get=get, now=NOW) == {"status": "ok", "sessions": 2}
    assert asked == [INDEX_SESSIONS_URL] and "code:VNINDEX" in asked[0] and "date:gte:2013-01-01" in asked[0]
    assert read_index_sessions(tmp_path) == {"source": "vndirect:finfo", "fetched_at": NOW.isoformat(), "dates": ["2013-01-02", "2013-01-03"]}
    assert sync_index_sessions(tmp_path, get=lambda url: json.dumps({"data": []}), now=NOW) == {"status": "empty", "sessions": 0}
    assert read_index_sessions(tmp_path)["dates"] == ["2013-01-02", "2013-01-03"]  # an empty answer keeps what was stored


def test_a_run_before_the_close_keeps_no_price_of_the_session_still_trading(tmp_path):
    # 26/11/2026 13:46 in Hà Nội: VNDirect already lists 26/11 at the price of the moment, which is no close (owner, 26/11/2026)
    _listing(tmp_path, [])
    midday = datetime(2026, 11, 26, 6, 46, tzinfo=timezone.utc)
    get = lambda url: rows("KDH", [("2026-11-25", 14.95), ("2026-11-26", 14.3)])  # noqa: E731
    sync_price_history(tmp_path, get=get, now=midday, symbols=["KDH"], sleep=lambda s: None)
    assert PriceHistoryStore(tmp_path).read("KDH")["closes"] == [["2026-11-25", "14.95"]]
    evening = datetime(2026, 11, 26, 13, 0, tzinfo=timezone.utc)  # 20:00 in Hà Nội: the session is closed
    sync_price_history(tmp_path, get=get, now=evening, symbols=["KDH"], sleep=lambda s: None)
    assert PriceHistoryStore(tmp_path).read("KDH")["closes"][-1] == ["2026-11-26", "14.3"]
