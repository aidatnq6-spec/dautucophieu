"""Giỏ chiến lược: the owner's own baskets of holding periods and what each made, from the ledger. Personal data, never sent to a model."""

from decimal import Decimal

from pydantic import Field, model_validator

from investment_agent.domain.holding_periods import basket_view, holding_periods
from investment_agent.domain.models import ContractModel
from investment_agent.services.records import LedgerBook, read_version

RECORD = ("settings", "trade_baskets")
MAX_BASKETS = 8


class Basket(ContractModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    name: str = Field(min_length=1, max_length=40, pattern=r"\S")


class TradeBaskets(ContractModel):
    baskets: tuple[Basket, ...] = Field(default=(), max_length=MAX_BASKETS)
    tags: dict[str, str] = Field(default_factory=dict, max_length=2000)  # period key "SYMBOL@start" -> basket id

    @model_validator(mode="after")
    def _consistent(self):
        ids = [b.id for b in self.baskets]
        if len(set(ids)) != len(ids):
            raise ValueError("basket ids must be unique")
        if len({b.name.strip().casefold() for b in self.baskets}) != len(self.baskets):
            raise ValueError("basket names must be unique")
        if any(v not in ids for v in self.tags.values()):
            raise ValueError("a tag names a basket that does not exist")
        return self


def read_baskets(repo, owner) -> tuple[TradeBaskets, int]:
    record = read_version(repo, owner, *RECORD, None)
    return (TradeBaskets.model_validate(record.payload), record.version) if record else (TradeBaskets(), 0)


def baskets_for(repo, owner, market) -> dict:
    """Raises RepositoryUnavailable. Open periods are valued at the market's last price, as the Danh mục table."""
    data, version = read_baskets(repo, owner)
    periods = holding_periods(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events))
    prices: dict[str, Decimal] = {}
    for symbol in {p["symbol"] for p in periods if not p["end"]}:
        point = market.price(symbol) if market is not None else None
        if point is not None:
            prices[symbol] = point.price
    dumped = data.model_dump(mode="json")
    return {"version": version, "data": dumped, "view": basket_view(periods, dumped, prices=prices)}
