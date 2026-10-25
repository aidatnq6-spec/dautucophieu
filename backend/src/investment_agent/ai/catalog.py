"""OpenRouter model catalog snapshot (GET /api/v1/models): per-token USD prices as Decimal, fetch time kept.

A price that is missing, empty or negative is unknown — never zero.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

MODELS_URL = "https://openrouter.ai/api/v1/models"


@dataclass(frozen=True)
class CatalogModel:
    id: str
    prompt_price: Decimal | None
    completion_price: Decimal | None
    supported_parameters: frozenset[str]
    context_length: int | None


@dataclass(frozen=True)
class Catalog:
    models: dict[str, CatalogModel]
    fetched_at: datetime


def _price(value) -> Decimal | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        price = Decimal(value)
    except InvalidOperation:
        return None
    return price if price.is_finite() and price >= 0 else None


def parse_catalog(payload: dict, *, fetched_at: datetime) -> Catalog:
    if fetched_at.tzinfo is None:
        raise ValueError("fetch time requires timezone")
    models = {}
    for m in payload.get("data", []):
        pricing = m.get("pricing") or {}
        models[m["id"]] = CatalogModel(id=m["id"], prompt_price=_price(pricing.get("prompt")), completion_price=_price(pricing.get("completion")),
                                       supported_parameters=frozenset(m.get("supported_parameters") or ()), context_length=m.get("context_length"))
    return Catalog(models=models, fetched_at=fetched_at)
