import json
from datetime import date

from investment_agent.market.index_valuation import fetch_index_valuation
from investment_agent.market.series import SeriesStore


def _page(code, ratio, rows):
    """Shape of api-finfo.vndirect.com.vn/v4/ratios as served on 31/10/2026 (fields trimmed to those read)."""
    return json.dumps({"data": [{"code": code, "group": "MARKET", "reportDate": d, "ratioCode": ratio, "value": v} for d, v in rows],
                       "currentPage": 1, "size": len(rows), "totalElements": len(rows), "totalPages": 1})


def test_first_sync_takes_the_whole_history_and_later_ones_only_recent_days(tmp_path):
    urls = []

    def get(url):
        urls.append(url)
        ratio = "PRICE_TO_EARNINGS" if "PRICE_TO_EARNINGS" in url else "PRICE_TO_BOOK"
        code = "VN30" if "code:VN30" in url else "VNINDEX"
        return _page(code, ratio, [("2026-10-29", 12.13), ("2026-10-30", 11.29)])

    store = SeriesStore(tmp_path)
    assert fetch_index_valuation(store, get=get, today=date(2026, 10, 31)) == {
        "VNINDEX-pe": "ok", "VNINDEX-pb": "ok", "VN30-pe": "ok", "VN30-pb": "ok"}
    assert len(urls) == 4 and all("reportDate:gte:2017-01-01" in u for u in urls)
    assert [v for _, v in store.read("VNINDEX-pe-1d")] == [12.13, 11.29]
    urls.clear()
    fetch_index_valuation(store, get=get, today=date(2026, 10, 31))
    assert all("reportDate:gte:2026-10-16" in u for u in urls)  # 14 days before the latest stored date


def test_rows_for_another_index_or_ratio_and_non_positive_values_are_dropped(tmp_path):
    def get(url):
        return _page("VNINDEX", "PRICE_TO_EARNINGS", [("2026-10-28", 0), ("2026-10-29", None), ("2026-10-30", 11.29)]) if "code:VNINDEX" in url \
            else _page("VNINDEX", "PRICE_TO_EARNINGS", [("2026-10-30", 15.0)])  # VN30 asked, VNINDEX answered

    store = SeriesStore(tmp_path)
    results = fetch_index_valuation(store, get=get, today=date(2026, 10, 31))
    assert [v for _, v in store.read("VNINDEX-pe-1d")] == [11.29]
    assert results["VN30-pe"] == "error:no_observations" and store.read("VN30-pe-1d") == []


def test_a_failing_source_is_reported_and_the_others_still_update(tmp_path):
    def get(url):
        if "PRICE_TO_BOOK" in url:
            raise OSError("timeout")
        return _page("VN30" if "code:VN30" in url else "VNINDEX", "PRICE_TO_EARNINGS", [("2026-10-30", 11.29)])

    results = fetch_index_valuation(SeriesStore(tmp_path), get=get, today=date(2026, 10, 31), sleep=lambda s: None)
    assert results == {"VNINDEX-pe": "ok", "VNINDEX-pb": "error:OSError", "VN30-pe": "ok", "VN30-pb": "error:OSError"}


def test_cli_index_valuation_sync_reports_each_series(tmp_path, capsys):
    from investment_agent.cli import index_valuation_sync

    def get(url):
        return _page("VN30" if "code:VN30" in url else "VNINDEX", "PRICE_TO_EARNINGS" if "EARNINGS" in url else "PRICE_TO_BOOK",
                     [("2026-10-30", 11.29)])

    assert index_valuation_sync(tmp_path, get=get, today=date(2026, 10, 31)) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
    assert SeriesStore(tmp_path / "index-valuation").read("VN30-pb-1d")
