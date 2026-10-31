"""Local views shared by the web routes and scheduled commands: held tickers and the Định giá board.

These read personal data and stay on the owner's machine; nothing here is ever sent to a model.
"""

from datetime import date
from pathlib import Path

from investment_agent.domain.ledger import replay
from investment_agent.market.financial_ratios import FinancialRatioStore
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.index_valuation import INDICES, series_key
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.services.records import LedgerBook, read_version, valuation_settings
from investment_agent.valuation.index_reference import value_index
from investment_agent.valuation.reference import Settings, reference_board, year_end_prices


def held_from_repo(repo, owner) -> set[str]:
    """Tickers with shares in the owner's ledger; raises RepositoryUnavailable."""
    book = LedgerBook(read_version(repo, owner, "ledger_events", "main", None))
    return {p.security_id for p in replay(list(book.effective().events)).positions if p.quantity + p.pending_quantity > 0}


def _bank_figures(repo, owner, symbols, sectors) -> dict[str, dict]:
    """Owner-entered quarterly bank figures (Số liệu ngân hàng), values only, for the banks' health score."""
    out = {}
    for s in symbols:
        if sectors.get(s) == "Ngân hàng" and (record := read_version(repo, owner, "settings", f"bank_figures_{s}", None)):
            out[s] = {q: v["values"] for q, v in record.payload.get("quarters", {}).items()}
    return out


def fair_value_board(data_dir: Path, market, repo, owner, *, held: set[str], today: date) -> dict:
    """Reference valuation of the watched tickers; raises RepositoryUnavailable."""
    settings, _ = valuation_settings(repo, owner)
    data_dir = Path(data_dir)
    symbols = list(load_watchlist(data_dir).symbols)
    store, series = FundamentalsStore(data_dir / "fundamentals"), SeriesStore(data_dir / "trend-sources")
    records = {s: store.read(s) for s in symbols}
    prices = {s: p.price for s in symbols if (p := market.price(s)) is not None}
    s = Settings(settings.required_return, settings.long_term_growth, settings.threshold)
    ratio_store = FinancialRatioStore(data_dir / "financial-ratios")
    sectors = load_sectors(data_dir)[0]
    board = reference_board(symbols, sectors=sectors, records=records, prices=prices,
                            year_end={t: year_end_prices(series.read(f"{t}-1d"), today=today) for t in symbols}, settings=s, today=today, held=held,
                            ratios={t: ratio_store.read(t) for t in symbols}, bank=_bank_figures(repo, owner, symbols, sectors))
    multiples = SeriesStore(data_dir / "index-valuation")
    board["indices"] = [value_index(i, pe=multiples.read(series_key(i, "pe")), pb=multiples.read(series_key(i, "pb")),
                                    closes=series.read(f"{i}-1d"), settings=s, today=today) for i in INDICES]
    return board
