"""Chuỗi giá trị content: config/value-chains.json, public knowledge committed and reviewed like code.

Every stage item and every macro factor cites at least one public source; a factor names a stored series (one of
macro-indicators.json or the commodity prices) or none when the app keeps no such series. The owner approves a chain by
switching its status from draft to approved.
"""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from investment_agent.domain.models import ContractModel
from investment_agent.domain.pinned import CONFIG_DIR
from investment_agent.domain.value_chain import weight_for_share

from .leading import CHAIN_SERIES, COMMODITIES, load_indicators

VALUE_CHAINS_PATH = CONFIG_DIR / "value-chains.json"
_SHARE = r"^0\.\d{1,4}(-0\.\d{1,4})?$"
# Display names of the commodity series (IMF Primary Commodity Prices on FRED).
COMMODITY_LABELS = {"com_coal": "Giá than thế giới (Úc)", "com_iron_ore": "Giá quặng sắt thế giới", "com_rubber": "Giá cao su thế giới",
                    "com_sugar": "Giá đường thế giới", "com_lng": "Giá khí LNG (Nhật Bản)",
                    "com_aluminium": "Giá nhôm thế giới", "com_copper": "Giá đồng thế giới", "com_wheat": "Giá lúa mì thế giới",
                    "com_soybean": "Giá đậu tương thế giới", "com_cotton": "Giá bông thế giới (Cotlook A, World Bank)", "crack_321_us": "Biên lọc dầu đại diện: crack 3-2-1 Mỹ (EIA qua FRED, USD/thùng)", "us_apparel_inv_ratio": "Tồn kho/doanh số cửa hàng quần áo Mỹ (Census qua FRED)", "com_urea": "Giá urê thế giới (Trung Đông, World Bank)",
                    "port_container_yoy": "Sản lượng container qua cảng Việt Nam so cùng kỳ (VPA)",
                    "com_dairy": "Chỉ số giá sữa thế giới (FAO)", "com_container_scfi": "Cước container xuất khẩu từ Thượng Hải (SCFI, Sở Giao dịch Vận tải biển Thượng Hải)",
                    "com_tanker_ctfi": "Cước tàu dầu thô chở về Trung Quốc (CTFI, Sở Giao dịch Vận tải biển Thượng Hải)",
                    "com_steel_hrc": "Giá thép cuộn cán nóng Trung Quốc (hợp đồng tương lai SHFE, CNY/tấn)",
                    "us_software_invest": "Đầu tư phần mềm của doanh nghiệp Mỹ theo quý (FRED/BEA; số đại diện, không có số của Nhật)",
                    "vn_hydro_inflow_yoy": "Lượng nước về các hồ thủy điện lớn so cùng kỳ năm trước (EVN)"}
COMMODITY_MAX_AGE_DAYS = 75  # monthly averages, published with about a month's lag
CHAIN_MAX_AGE_DAYS = {"vn_hydro_inflow_yoy": 7, "com_container_scfi": 14, "com_tanker_ctfi": 7, "com_steel_hrc": 10,
                      "us_software_invest": 220, "crack_321_us": 14, "us_apparel_inv_ratio": 110}  # daily and weekly series; a quarter (dated to its first day) is the latest until ~7 months on


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
    # an event (a tariff, a trade-defence case) is noted on the diagram and kept off the good/bad bar; it names no series
    kind: Literal["series", "event"] = "series"
    indicator: str | None
    when_up: Literal["good", "bad"]
    weight: Literal["major", "minor", "small"]
    share: str | None = Field(default=None, pattern=_SHARE)
    why: str = Field(min_length=1)
    refs: list[Ref] = Field(min_length=1)

    @model_validator(mode="after")
    def _weight_matches_share(self):
        if self.kind == "event" and self.indicator is not None:
            raise ValueError(f"factor {self.id}: an event names no series")
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
        known = {i["id"] for i in load_indicators()} | set(COMMODITIES) | set(CHAIN_SERIES)
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


def fingerprint(config: ValueChains, chain_id: str) -> str:
    """16 hex characters over the chain as the owner reads it (stages, factors, tickers) and the sources it cites; not its status.
    An approval in the app holds for this fingerprint only: any change to the content asks for approval again."""
    chain = next(c for c in config.chains if c.id == chain_id)
    body = chain.model_dump(mode="json", exclude={"status"})
    for f in body["factors"]:  # the kind came later: a plain series factor reads as before, so earlier approvals still hold
        if f["kind"] == "series":
            del f["kind"]
    cited = sorted({r.source for x in [*chain.stages.input, *chain.stages.middle, *chain.stages.output, *chain.factors] for r in x.refs})
    text = json.dumps({"chain": body, "sources": {k: config.sources[k].model_dump(mode="json") for k in cited}}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_value_chains(path: Path = VALUE_CHAINS_PATH) -> ValueChains:
    return ValueChains.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


# Giá đầu ra giảm nhưng dự phòng không đổi (owner, 23/11/2026): only prices of goods a company holds in stock. Coated steel ties HRC as its
# input, but its stock is HRC, so it counts; freight, gas into power and other inputs do not.
INVENTORY_PRICES = ("com_steel_hrc", "com_rubber", "com_urea", "com_sugar")


def inventory_price_series(data_dir: Path, symbol: str) -> tuple[str, str, list] | None:
    """(indicator, its label, [(date, price)] in order) for the ticker's goods price, from the stored macro series; None when the value
    chain ties none. A point that does not read as a positive number is left out, never repaired."""
    from datetime import date
    from decimal import Decimal, InvalidOperation
    from investment_agent.market.leading import MacroStore
    indicator = inventory_price_indicator(load_value_chains(), symbol)
    if indicator is None:
        return None
    points = []
    for o in MacroStore(Path(data_dir)).read(indicator):
        try:
            day, value = date.fromisoformat(str(o["date"])[:10]), Decimal(str(o["value"]))
        except (KeyError, ValueError, InvalidOperation):
            continue
        if value.is_finite() and value > 0:
            points.append((day, value))
    return indicator, COMMODITY_LABELS.get(indicator, indicator), sorted(points)


def inventory_price_indicator(config: ValueChains, symbol: str) -> str | None:
    """The goods price the ticker's value chain ties to it (with its refs), or None."""
    for chain in config.chains:
        if symbol in chain.symbols:
            for factor in chain.factors:
                if factor.indicator in INVENTORY_PRICES:
                    return factor.indicator
    return None
