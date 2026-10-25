"""What the model may see, defined by allowlisted fields rather than by scrubbing.

Allowed: tickers, portfolio weights rounded to 4 places, risk group, horizon
bucket, capacity flags, computed ratios, zone positions and public evidence
excerpts. Never: names, emails, account data, absolute cash/asset/income/debt
amounts, cost prices or transaction history.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import Field

from investment_agent.domain.ledger import LedgerState
from investment_agent.domain.models import ContractModel, NonemptyId, UnsignedAmount

WEIGHT_STEP = Decimal("0.0001")


class AiHolding(ContractModel):
    ticker: NonemptyId
    weight: UnsignedAmount | None  # share of investable capital; None when the price is unknown


class AiPortfolio(ContractModel):
    holdings: tuple[AiHolding, ...]
    cash_weight: UnsignedAmount | None
    risk_group: NonemptyId
    horizon_bucket: Literal["under_1y", "1_3y", "3_5y", "5y_plus"]
    capacity_flags: tuple[NonemptyId, ...]
    data_flags: tuple[NonemptyId, ...]


class EntityFacts(ContractModel):
    ticker: NonemptyId
    ratios: dict[str, str]
    zone: str | None


class EvidenceItem(ContractModel):
    evidence_id: NonemptyId
    kind: NonemptyId
    ticker: str | None
    source_url: str = Field(pattern=r"^https://\S+$")
    excerpt: str = Field(max_length=4000)


class AiPayload(ContractModel):
    payload_version: Literal["1"] = "1"
    portfolio: AiPortfolio
    entities: tuple[EntityFacts, ...]
    evidence: tuple[EvidenceItem, ...]


def _weight(value: Decimal, capital: Decimal) -> str:
    return format((value / capital).quantize(WEIGHT_STEP, rounding=ROUND_HALF_UP), "f")


def build_payload(*, state: LedgerState, prices: dict[str, Decimal], tickers: dict[str, str], investable_capital: Decimal,
                  risk_group: str, horizon_bucket: str, flags: list[str], ratios: dict[str, dict[str, str]], zones: dict[str, str],
                  evidence: list[EvidenceItem], owner: dict | None = None) -> AiPayload:
    """`owner` (identity data) is accepted from callers and deliberately never forwarded."""
    if investable_capital <= 0:
        raise ValueError("weights need positive investable capital")
    holdings, data_flags = [], []
    for h in state.positions:
        ticker = tickers[h.security_id]
        price = prices.get(h.security_id)
        if price is None:
            data_flags.append(f"price_missing:{ticker}")
        holdings.append(AiHolding(ticker=ticker, weight=None if price is None else _weight((h.quantity + h.pending_quantity) * price, investable_capital)))
    portfolio = AiPortfolio(holdings=tuple(holdings), cash_weight=_weight(state.cash, investable_capital), risk_group=risk_group,
                            horizon_bucket=horizon_bucket, capacity_flags=tuple(flags), data_flags=tuple(data_flags))
    entities = tuple(EntityFacts(ticker=t, ratios=r, zone=zones.get(t)) for t, r in sorted(ratios.items()))
    return AiPayload(portfolio=portfolio, entities=entities, evidence=tuple(evidence))
