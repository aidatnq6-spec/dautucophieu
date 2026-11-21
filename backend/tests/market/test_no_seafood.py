"""The owner removed Thủy sản and VHC, ANV from the application on 21/11/2026: no Thủy sản value chain, and the two series that served
only it (VASEP's cá tra exports, FRED's world shrimp price) are no longer read or offered."""

import json

from investment_agent.market.leading import CHAIN_SERIES, COMMODITIES
from investment_agent.market.value_chains import COMMODITY_LABELS, VALUE_CHAINS_PATH, load_value_chains


def test_no_value_chain_is_about_seafood_or_names_vhc_or_anv():
    chains = load_value_chains().chains
    assert not [c.id for c in chains if c.id == "seafood" or c.name == "Thủy sản"]
    raw = json.loads(VALUE_CHAINS_PATH.read_text(encoding="utf-8"))
    assert not [c["id"] for c in raw["chains"] if {"VHC", "ANV"} & set(c.get("symbols", []))]
    assert "vasep" not in json.dumps(raw).lower()


def test_pangasius_exports_and_the_shrimp_price_are_no_longer_read_or_offered():
    from investment_agent.domain.value_chain import GROWTH
    from investment_agent.services.early_lights import _COMMODITIES
    assert "vn_pangasius_export_yoy" not in CHAIN_SERIES and "vn_pangasius_export_yoy" not in GROWTH
    assert "com_shrimp" not in COMMODITIES and "com_shrimp" not in _COMMODITIES
    assert not {"com_shrimp", "vn_pangasius_export_yoy"} & set(COMMODITY_LABELS)
