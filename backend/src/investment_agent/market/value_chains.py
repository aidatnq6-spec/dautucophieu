"""Chuỗi giá trị content: config/value-chains.json, public knowledge committed and reviewed like code.

Every stage item and every macro factor cites at least one public source; a factor names a stored series (one of
macro-indicators.json or the commodity prices) or none when the app keeps no such series. The owner approves a chain by
switching its status from draft to approved.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from investment_agent.domain.models import ContractModel
from investment_agent.domain.pinned import CONFIG_DIR
from investment_agent.domain.value_chain import weight_for_share

from .leading import COMMODITIES, load_indicators

VALUE_CHAINS_PATH = CONFIG_DIR / "value-chains.json"
_SHARE = r"^0\.\d{1,4}(-0\.\d{1,4})?$"
# Display names of the commodity series (IMF Primary Commodity Prices on FRED).
COMMODITY_LABELS = {"com_coal": "Giá than thế giới (Úc)", "com_iron_ore": "Giá quặng sắt thế giới", "com_rubber": "Giá cao su thế giới",
                    "com_sugar": "Giá đường thế giới", "com_shrimp": "Giá tôm thế giới", "com_lng": "Giá khí LNG (Nhật Bản)",
                    "com_aluminium": "Giá nhôm thế giới", "com_copper": "Giá đồng thế giới", "com_wheat": "Giá lúa mì thế giới",
                    "com_soybean": "Giá đậu tương thế giới"}
COMMODITY_MAX_AGE_DAYS = 75  # monthly averages, published with about a month's lag


class Source(ContractModel):
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    date: str = Field(pattern=r"^\d{4}-\d{2}(-\d{2})?$")  # a month alone when the document gives no day
    url: str = Field(pattern=r"^https?://\S+$")


class Ref(ContractModel):
    source: str
    page: int | None = Field(default=None, ge=1)


class Item(ContractModel):
    name: str = Field(min_length=1)
    note: str | None = None
    share: str | None = Field(default=None, pattern=_SHARE)
    basis: str | None = None  # what the share is of: giá thành, doanh thu, …
    refs: list[Ref] = Field(min_length=1)


class Factor(ContractModel):
    id: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    label: str = Field(min_length=1)
    stage: Literal["input", "middle", "output"]
    indicator: str | None
    when_up: Literal["good", "bad"]
    weight: Literal["major", "minor", "small"]
    share: str | None = Field(default=None, pattern=_SHARE)
    why: str = Field(min_length=1)
    refs: list[Ref] = Field(min_length=1)

    @model_validator(mode="after")
    def _weight_matches_share(self):
        if self.share is not None and weight_for_share(self.share) != self.weight:
            raise ValueError(f"factor {self.id}: share {self.share} is {weight_for_share(self.share)}, not {self.weight}")
        return self


class Stages(ContractModel):
    input: list[Item] = Field(min_length=1)
    middle: list[Item] = Field(min_length=1)
    output: list[Item] = Field(min_length=1)


class Chain(ContractModel):
    id: str = Field(pattern=r"^[a-z0-9-]{1,40}$")
    name: str = Field(min_length=1)
    icb: str = Field(min_length=1)
    status: Literal["draft", "approved"]
    symbols: list[str] = Field(min_length=1)
    stages: Stages
    factors: list[Factor] = Field(min_length=1)


class ValueChains(ContractModel):
    version: str
    sources: dict[str, Source]
    chains: list[Chain]

    @model_validator(mode="after")
    def _consistent(self):
        known = {i["id"] for i in load_indicators()} | set(COMMODITIES)
        ids, owner = set(), {}
        for chain in self.chains:
            if chain.id in ids:
                raise ValueError(f"chain {chain.id} appears twice")
            ids.add(chain.id)
            for symbol in chain.symbols:
                if symbol in owner:
                    raise ValueError(f"{symbol} is in both {owner[symbol]} and {chain.id}")
                owner[symbol] = chain.id
            items = [*chain.stages.input, *chain.stages.middle, *chain.stages.output]
            if len({f.id for f in chain.factors}) != len(chain.factors):
                raise ValueError(f"chain {chain.id}: factor ids repeat")
            for ref in (r for x in [*items, *chain.factors] for r in x.refs):
                if ref.source not in self.sources:
                    raise ValueError(f"chain {chain.id}: unknown source {ref.source}")
            for f in chain.factors:
                if f.indicator is not None and f.indicator not in known:
                    raise ValueError(f"chain {chain.id}: unknown series {f.indicator}")
        return self


def load_value_chains(path: Path = VALUE_CHAINS_PATH) -> ValueChains:
    return ValueChains.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
