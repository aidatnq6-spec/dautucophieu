"""The owner's choice of 21/11/2026 for the seven watched tickers without a chain: BMI to Bảo hiểm, TLG to Hàng tiêu dùng, and three
new draft chains from public reports: Tôn mạ (HSG, NKG), Xăng dầu (BSR, PLX), Dệt may (MSH)."""

from investment_agent.market.leading import WB_COMMODITIES
from investment_agent.market.value_chains import COMMODITY_LABELS, load_value_chains


def chains():
    return {c.id: c for c in load_value_chains().chains}


def test_bmi_and_tlg_join_existing_chains():
    c = chains()
    assert "BMI" in c["insurance"].symbols and "TLG" in c["consumer"].symbols


def test_coated_steel_reads_hrc_as_a_cost_and_trade_defence_as_bad():
    steel = chains()["coated-steel"]
    assert (steel.name, steel.status, steel.symbols) == ("Tôn mạ", "draft", ["HSG", "NKG"])
    f = {x.id: x for x in steel.factors}
    assert (f["hrc_price"].indicator, f["hrc_price"].stage, f["hrc_price"].when_up) == ("com_steel_hrc", "input", "bad")
    assert all(f[k].kind == "event" and f[k].when_up == "bad" for k in ("hrc_trade_defence", "export_trade_cases"))


def test_fuel_chain_names_the_crack_spread_it_cannot_measure():
    fuel = chains()["fuel"]
    assert (fuel.name, fuel.status, fuel.symbols) == ("Xăng dầu", "draft", ["BSR", "PLX"])
    f = {x.id: x for x in fuel.factors}
    assert f["crack_spread"].indicator is None and f["crude"].indicator == "brent" and f["retail_price"].indicator == "vn_ron95_price"
    assert f["pricing_decree"].kind == "event"


def test_garment_chain_reads_the_world_cotton_price():
    garment = chains()["garment"]
    assert (garment.name, garment.status, garment.symbols) == ("Dệt may", "draft", ["MSH"])
    f = {x.id: x for x in garment.factors}
    assert (f["cotton"].indicator, f["cotton"].when_up) == ("com_cotton", "bad")
    assert f["us_demand"].indicator is None and f["us_tariff"].kind == "event"
    assert WB_COMMODITIES["com_cotton"] == "Cotton, A Index" and "com_cotton" in COMMODITY_LABELS
