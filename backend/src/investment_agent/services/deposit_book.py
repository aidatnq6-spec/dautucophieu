"""Sổ tài sản on Hồ sơ & rủi ro: the stored book (`settings/deposit_book`), its maturity calendar, and cash now against the reserve
Tháp tài sản uses (entered in the book; blank = the profile's). Personal data; never sent to a model."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from investment_agent.domain.deposit_book import DepositBook, bond_values, gold_values, liquidity, maturity_calendar
from investment_agent.domain.ledger import replay
from investment_agent.market.fund_nav import fund_navs
from investment_agent.market.gold_price import gold_prices
from investment_agent.services.records import LedgerBook, read_version

RECORD = ("settings", "deposit_book")


def read_book(repo, owner) -> tuple[DepositBook | None, int]:
    """(book, version); None before the first save."""
    stored = read_version(repo, owner, *RECORD, None)
    return (DepositBook.model_validate(stored.payload), stored.version) if stored else (None, 0)


def book_at(repo, owner, cutoff) -> DepositBook | None:
    """The book as last saved at or before cutoff (an aware datetime); None when it had not been saved yet. Every save is kept as
    its own revision with the time it was written, so this is the book as it stood, not a reconstruction."""
    from datetime import datetime
    head = read_version(repo, owner, *RECORD, None)
    if head is None:
        return None
    when = lambda r: datetime.fromisoformat(r.created_at)  # noqa: E731 - revisions are written in order, so their times only grow
    if when(head) <= cutoff:
        return DepositBook.model_validate(head.payload)
    lo, hi, found = 1, head.version - 1, None  # halving: a few reads, not one per revision (4 s on a book saved many times)
    while lo <= hi:
        mid = (lo + hi) // 2
        record = read_version(repo, owner, *RECORD, mid)
        if record is not None and when(record) <= cutoff:
            found, lo = record, mid + 1
        else:
            hi = mid - 1
    return DepositBook.model_validate(found.payload) if found else None


def ledger_cash(repo, owner) -> Decimal:
    return replay(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)).cash


def book_quotes(data_dir: Path | None) -> dict:
    """Public prices the book's rows are valued at: {"funds": fund NAVs (Fmarket), "gold": Phú Quý prices}; empty before the first sync."""
    return {"funds": fund_navs(data_dir), "gold": gold_prices(data_dir)}


def book_view(repo, owner, *, reserve: Decimal, profile_reserve: Decimal, quotes: dict, today: date) -> dict:
    """reserve: the deductions Tháp tài sản uses (services.equity_budget.protected_deductions); profile_reserve: the confirmed profile's
    figure, used when the book's reserve is blank; quotes: book_quotes()."""
    book, version = read_book(repo, owner)
    book = book or DepositBook()
    return {"version": version, "book": book.model_dump(mode="json"), "calendar": maturity_calendar(book, today=today),
            "liquidity": liquidity(book, ledger_cash=ledger_cash(repo, owner), reserve=reserve, today=today),
            "profile_reserve": format(profile_reserve, "f"), "bond_values": bond_values(book, quotes["funds"], today=today),
            "nav_source": "Fmarket" if quotes["funds"] else None, "gold_values": gold_values(book, quotes["gold"], today=today),
            "gold_kinds": list((quotes["gold"].get("kinds") or {})), "gold_source": quotes["gold"].get("source"),
            "gold_as_of": quotes["gold"].get("as_of")}
