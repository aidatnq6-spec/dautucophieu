"""Giỏ chiến lược: the owner's own baskets of holding periods and what each made, from the ledger. Personal data, never sent to a model."""

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from investment_agent.domain.holding_periods import basket_view, holding_periods
from investment_agent.domain.models import ContractModel, Ratio, UnsignedAmount
from investment_agent.services.records import LedgerBook, PortfolioSettings, portfolio_settings, read_version

RECORD = ("settings", "trade_baskets")
MAX_BASKETS = 8


Mode = Literal["default", "custom", "off"]


class DrawdownRule(ContractModel):
    """Kế hoạch sụt giảm for a basket: the common level (default), its own % below cost, or no reminder."""
    mode: Mode = "default"
    threshold: Ratio | None = None

    @model_validator(mode="after")
    def _whole(self):
        if self.mode == "custom" and (self.threshold is None or not Decimal("0.01") <= self.threshold <= Decimal("0.95")):
            raise ValueError("a basket's own drawdown level must be between 1% and 95%")
        if self.mode != "custom":
            self.threshold = None
        return self


class GivebackRule(ContractModel):
    """Lãi đã trả lại thị trường for a basket: the common A and B (default), its own A and B together, or no reminder."""
    mode: Mode = "default"
    min_gain: UnsignedAmount | None = None
    share: Ratio | None = None

    @model_validator(mode="after")
    def _whole(self):
        if self.mode == "custom":
            if self.min_gain is None or self.share is None:
                raise ValueError("a basket's own giveback levels need both A and B")
            if not Decimal("0.01") <= self.min_gain <= Decimal("10") or not Decimal("0.01") <= self.share <= Decimal("1"):
                raise ValueError("a basket's own giveback levels are out of range")
        else:
            self.min_gain = self.share = None
        return self


class Basket(ContractModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    name: str = Field(min_length=1, max_length=40, pattern=r"\S")
    drawdown: DrawdownRule = Field(default_factory=DrawdownRule)  # older baskets have neither: the common level
    giveback: GivebackRule = Field(default_factory=GivebackRule)


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


def _s(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def common_rules(settings: PortfolioSettings, basket: str | None = None) -> dict:
    return {"drawdown": {"source": "default", "basket": basket, "threshold": _s(settings.drawdown_threshold)},
            "giveback": {"source": "default", "basket": basket, "min_gain": _s(settings.giveback_min_gain), "share": _s(settings.giveback_share)}}


def resolve_rules(periods: list[dict], data: TradeBaskets, settings: PortfolioSettings) -> dict[str, dict]:
    """{symbol: {drawdown, giveback}} for each ticker held now, from the basket of its current holding period. A period with no basket, or a
    basket left at the common level, takes the levels in Cài đặt; a basket set to no reminder gives no level ("source": "off")."""
    by_id = {b.id: b for b in data.baskets}
    out = {}
    for p in periods:
        if p["end"]:
            continue
        b = by_id.get(data.tags.get(p["key"], ""))
        rules = common_rules(settings, b.name if b else None)
        if b and b.drawdown.mode != "default":
            rules["drawdown"] = {"source": "basket" if b.drawdown.mode == "custom" else "off", "basket": b.name, "threshold": _s(b.drawdown.threshold)}
        if b and b.giveback.mode != "default":
            rules["giveback"] = {"source": "basket" if b.giveback.mode == "custom" else "off", "basket": b.name,
                                 "min_gain": _s(b.giveback.min_gain), "share": _s(b.giveback.share)}
        out[p["symbol"]] = rules
    return out


def rules_for(repo, owner) -> dict[str, dict]:
    """Raises RepositoryUnavailable."""
    periods = holding_periods(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events))
    return resolve_rules(periods, read_baskets(repo, owner)[0], portfolio_settings(repo, owner)[0])


def _pct(ratio: str) -> str:
    return format((Decimal(ratio) * 100).normalize(), "f").replace(".", ",") + "%"


def rule_label(rule: dict, kind: str) -> str:
    """Where a ticker's level comes from, for the page and the reminder: "giỏ Ngắn hạn: 7%", "mức chung: 30%", "giỏ Dài hạn: không nhắc"."""
    head = "mức chung" if rule["source"] == "default" else f"giỏ {rule['basket']}"
    if rule["source"] == "off":
        return f"{head}: không nhắc"
    if kind == "drawdown":
        return f"{head}: {_pct(rule['threshold'])}"
    if rule["min_gain"] is None:
        return f"{head}: chưa đặt"
    return f"{head}: lãi từ {_pct(rule['min_gain'])}, trả lại từ {_pct(rule['share'])}"
