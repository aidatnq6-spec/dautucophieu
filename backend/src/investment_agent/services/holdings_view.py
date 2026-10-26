"""Local views shared by the web routes and scheduled commands: held tickers and the Định giá board.

These read personal data and stay on the owner's machine; nothing here is ever sent to a model.
"""

from datetime import date
from pathlib import Path

from investment_agent.domain.ledger import replay
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.services.records import LedgerBook, read_version, valuation_settings
from investment_agent.valuation.reference import Settings, reference_board, year_end_prices


def held_from_repo(repo, owner) -> set[str]:
    """Tickers with shares in the owner's ledger; raises RepositoryUnavailable."""
    book = LedgerBook(read_version(repo, owner, "ledger_events", "main", None))
    return {p.security_id for p in replay(list(book.effective().events)).positions if p.quantity + p.pending_quantity > 0}


def fair_value_board(data_dir: Path, market, repo, owner, *, held: set[str], today: date) -> dict:
    """Reference valuation of the watched tickers; raises RepositoryUnavailable."""
    settings, _ = valuation_settings(repo, owner)
    data_dir = Path(data_dir)
    symbols = list(load_watchlist(data_dir).symbols)
    store, series = FundamentalsStore(data_dir / "fundamentals"), SeriesStore(data_dir / "trend-sources")
    records = {s: store.read(s) for s in symbols}
    prices = {s: p.price for s in symbols if (p := market.price(s)) is not None}
    return reference_board(symbols, sectors=load_sectors(data_dir)[0], records=records, prices=prices,
                           year_end={s: year_end_prices(series.read(f"{s}-1d"), today=today) for s in symbols},
                           settings=Settings(settings.required_return, settings.long_term_growth, settings.threshold), today=today, held=held)
