from datetime import date
from decimal import Decimal

from investment_agent.market.view import PricePoint, SyntheticMarket
from investment_agent.services.deposit_book import book_quotes


def test_stock_prices_come_from_the_market_given_and_are_missing_without_one(tmp_path):
    market = SyntheticMarket(prices={"FPT": PricePoint(Decimal(60_000), date(2026, 11, 20))})
    price = book_quotes(tmp_path, market)["stocks"]
    assert price("FPT") == PricePoint(Decimal(60_000), date(2026, 11, 20)) and price("HPG") is None
    assert book_quotes(None)["stocks"]("FPT") is None
    assert book_quotes(tmp_path)["stocks"]("FPT") is None  # no price store yet


def test_the_stored_prices_of_one_data_folder_share_one_price_store(tmp_path):
    """Each call used to open a new price store, so Việc cần xem re-read every held ticker's files on each Tổng quan (0.1 s)."""
    (tmp_path / "prices").mkdir()
    first, second = book_quotes(tmp_path)["stocks"], book_quotes(tmp_path)["stocks"]
    assert first.__self__.store is second.__self__.store
