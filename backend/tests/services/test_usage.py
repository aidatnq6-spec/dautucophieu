"""Sử dụng phần mềm (owner, 21/11/2026): how often each page is opened and which requests were slow, kept on this computer only
(data/usage) to choose the next improvements. Paths are masked: a ticker or an amount never lands in the file."""

from datetime import date, datetime, timezone

from investment_agent.services.usage import mask_path, page_key, record_slow, record_visit, usage_summary

TODAY = date(2026, 11, 21)


def test_a_page_is_counted_by_its_first_segment_and_anything_else_is_refused():
    assert page_key("/") == "/" and page_key("/macro") == "/macro" and page_key("/research/HPG") == "/research"
    assert page_key("/fair-value?x=1") == "/fair-value"
    assert page_key("macro") is None and page_key("/../etc") is None and page_key("/" + "a" * 50) is None


def test_a_slow_path_keeps_its_words_and_masks_tickers_and_amounts():
    assert mask_path("/internal/concentration/whatif/FPT/300000000") == "/internal/concentration/whatif/*/*"
    assert mask_path("/internal/fairvalue/history/HPG") == "/internal/fairvalue/history/*"
    assert mask_path("/internal/glance") == "/internal/glance"


def test_visits_are_counted_per_day_and_summed_over_30_and_7_days(tmp_path):
    for day, page, n in ((date(2026, 10, 1), "/macro", 5), (date(2026, 11, 1), "/macro", 2), (TODAY, "/macro", 1), (TODAY, "/", 3)):
        for _ in range(n):
            record_visit(tmp_path, page, today=day)
    out = usage_summary(tmp_path, today=TODAY)
    assert out["pages"] == [{"page": "/", "last_30": 3, "last_7": 3, "today": 3, "last_day": "2026-11-21"},
                            {"page": "/macro", "last_30": 3, "last_7": 1, "today": 1, "last_day": "2026-11-21"}]


def test_days_older_than_90_are_dropped(tmp_path):
    record_visit(tmp_path, "/macro", today=date(2026, 8, 1))
    record_visit(tmp_path, "/macro", today=TODAY)
    import json
    days = json.loads((tmp_path / "usage" / "visits.json").read_text(encoding="utf-8"))["days"]
    assert list(days) == ["2026-11-21"]


def test_slow_requests_are_kept_newest_first_and_grouped_by_masked_path(tmp_path):
    at = lambda h: datetime(2026, 11, 21, h, tzinfo=timezone.utc)  # noqa: E731
    record_slow(tmp_path, method="GET", path="/internal/fairvalue/history/HPG", seconds=1.4, status=200, at=at(1))
    record_slow(tmp_path, method="GET", path="/internal/fairvalue/history/FPT", seconds=2.25, status=200, at=at(2))
    record_slow(tmp_path, method="GET", path="/internal/glance", seconds=1.1, status=200, at=at(3))
    out = usage_summary(tmp_path, today=TODAY)
    assert out["slow"] == [{"path": "GET /internal/fairvalue/history/*", "count": 2, "worst": "2.25", "last": at(2).isoformat()},
                           {"path": "GET /internal/glance", "count": 1, "worst": "1.10", "last": at(3).isoformat()}]
    assert out["slow_threshold"] == "1.0"


def test_only_the_last_200_slow_requests_are_kept(tmp_path):
    import json
    for i in range(205):
        record_slow(tmp_path, method="GET", path="/internal/glance", seconds=1.5, status=200, at=datetime(2026, 11, 21, tzinfo=timezone.utc))
    assert len(json.loads((tmp_path / "usage" / "slow.json").read_text(encoding="utf-8"))) == 200


def test_nothing_recorded_reads_as_empty(tmp_path):
    assert usage_summary(tmp_path, today=TODAY) == {"pages": [], "slow": [], "slow_threshold": "1.0", "since": None}
