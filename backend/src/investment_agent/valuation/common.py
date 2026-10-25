"""Shared result shape for sector models; every value names its approved assumption version."""

from decimal import Decimal
from typing import Literal

from pydantic import Field

from investment_agent.domain.models import ContractModel, SignedAmount


class ApprovalRef(ContractModel):
    assumption_version: int = Field(strict=True, ge=1)
    approved: bool


class SectorResult(ContractModel):
    model: Literal["residual_income", "nav", "cyclical_normalized"]
    status: Literal["draft", "approved", "unavailable"]
    reason: str | None = None
    equity_value: SignedAmount | None = None
    per_share: SignedAmount | None = None
    flags: tuple[str, ...] = ()
    assumption_version: int
    buy_zone_active: bool


def s(value: Decimal) -> str:
    return format(value, "f")


def finish(model, ref, equity: Decimal | None, shares: int | None, *, flags=(), reason=None, **extra) -> dict:
    if equity is None or shares is None:
        return dict(model=model, status="unavailable", reason=reason or "inputs_missing", assumption_version=ref.assumption_version,
                    buy_zone_active=False, flags=tuple(flags), **extra)
    status = "approved" if ref.approved else "draft"
    return dict(model=model, status=status, reason=reason, equity_value=s(equity), per_share=s(equity / shares), flags=tuple(flags),
                assumption_version=ref.assumption_version, buy_zone_active=status == "approved" and not flags, **extra)
