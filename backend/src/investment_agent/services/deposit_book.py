"""Sổ tiền gửi on Hồ sơ & rủi ro: the stored book (`settings/deposit_book`), its maturity calendar, and cash now against the reserve
Tháp tài sản uses. Personal data; never sent to a model."""

from datetime import date
from decimal import Decimal

from investment_agent.domain.deposit_book import DepositBook, liquidity, maturity_calendar
from investment_agent.domain.ledger import replay
from investment_agent.services.records import LedgerBook, read_version

RECORD = ("settings", "deposit_book")


def read_book(repo, owner) -> tuple[DepositBook | None, int]:
    """(book, version); None before the first save."""
    stored = read_version(repo, owner, *RECORD, None)
    return (DepositBook.model_validate(stored.payload), stored.version) if stored else (None, 0)


def ledger_cash(repo, owner) -> Decimal:
    return replay(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)).cash


def book_view(repo, owner, *, reserve: Decimal, today: date) -> dict:
    """reserve: the deductions Tháp tài sản uses (services.equity_budget.protected_deductions)."""
    book, version = read_book(repo, owner)
    book = book or DepositBook()
    return {"version": version, "book": book.model_dump(mode="json"), "calendar": maturity_calendar(book, today=today),
            "liquidity": liquidity(book, ledger_cash=ledger_cash(repo, owner), reserve=reserve, today=today)}
