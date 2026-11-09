"""Local views shared by the web routes and scheduled commands: held tickers and the Định giá board.

These read personal data and stay on the owner's machine; nothing here is ever sent to a model.
"""

from datetime import date
from pathlib import Path

from investment_agent.domain.ledger import replay
from investment_agent.market.financial_ratios import FinancialRatioStore
from investment_agent.market.index_valuation import INDICES, series_key
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import prefetch
from investment_agent.valuation.sources import merged_fundamentals
from investment_agent.services.records import LedgerBook, read_version, valuation_settings
from investment_agent.valuation.index_reference import value_index
from investment_agent.valuation.reference import Settings, reference_board, year_end_prices


def held_from_repo(repo, owner) -> set[str]:
    """Tickers with shares in the owner's ledger; raises RepositoryUnavailable."""
    book = LedgerBook(read_version(repo, owner, "ledger_events", "main", None))
    return {p.security_id for p in replay(list(book.effective().events)).positions if p.quantity + p.pending_quantity > 0}


def _bank_figures(repo, owner, data_dir: Path, symbols, sectors) -> dict[str, dict]:
    """Each watched bank's CASA and group-2 share by quarter for its health score: Vietcap's notes (data/bank-notes), with the
    quarters the owner entered (Số liệu ngân hàng) on top."""
    from investment_agent.market.bank_notes import BankNoteStore, bank_ratio_rows
    notes = BankNoteStore(Path(data_dir) / "bank-notes")
    out = {}
    banks = [s for s in symbols if sectors.get(s) == "Ngân hàng"]
    if repo is not None:  # one Firestore transaction each: read one after another they were more than half of the board's time
        prefetch(getattr(repo, "authoritative", repo), owner, [("settings", f"bank_figures_{s}") for s in banks])
    for s in banks:
        record = read_version(repo, owner, "settings", f"bank_figures_{s}", None) if repo is not None else None
        entered = {q: v["values"] for q, v in record.payload.get("quarters", {}).items()} if record else {}
        if rows := bank_ratio_rows(entered, (notes.read(s) or {}).get("quarters") or {}):
            out[s] = rows
    return out


def fair_value_board(data_dir: Path, market, repo, owner, *, held: set[str], today: date) -> dict:
    """Reference valuation of the watched tickers; raises RepositoryUnavailable."""
    settings, _ = valuation_settings(repo, owner)
    data_dir = Path(data_dir)
    symbols = list(load_watchlist(data_dir).symbols)
    series = SeriesStore(data_dir / "trend-sources")
    records = {s: merged_fundamentals(data_dir, s)[0] for s in symbols}  # VNDirect's parent figures when the ticker has them
    prices = {s: p.price for s in symbols if (p := market.price(s)) is not None}
    s = Settings(settings.required_return, settings.long_term_growth, settings.threshold)
    ratio_store = FinancialRatioStore(data_dir / "financial-ratios")
    sectors = load_sectors(data_dir)[0]
    board = reference_board(symbols, sectors=sectors, records=records, prices=prices,
                            year_end={t: year_end_prices(series.read(f"{t}-1d"), today=today) for t in symbols}, settings=s, today=today, held=held,
                            ratios={t: ratio_store.read(t) for t in symbols}, bank=_bank_figures(repo, owner, data_dir, symbols, sectors))
    multiples = SeriesStore(data_dir / "index-valuation")
    board["indices"] = [value_index(i, pe=multiples.read(series_key(i, "pe")), pb=multiples.read(series_key(i, "pb")),
                                    closes=series.read(f"{i}-1d"), settings=s, today=today) for i in INDICES]
    return board
