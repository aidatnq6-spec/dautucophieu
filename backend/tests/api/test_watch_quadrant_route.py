from signed_client import call
from test_deposit_book_route import client


def test_the_quadrant_lists_each_watched_ticker_or_why_it_is_not_drawn(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/watchlist/quadrant").json()
    assert body["points"] == [] and body["missing"] == {"FPT": "chưa đủ 24 tháng P/B"}  # no statements or prices stored
