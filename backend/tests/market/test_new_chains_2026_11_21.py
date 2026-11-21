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
    assert f["crack_spread"].indicator == "crack_321_us" and f["crude"].indicator == "brent" and f["retail_price"].indicator == "vn_ron95_price"
    assert f["pricing_decree"].kind == "event"


def test_garment_chain_reads_the_world_cotton_price():
    garment = chains()["garment"]
    assert (garment.name, garment.status, garment.symbols) == ("Dệt may", "draft", ["MSH"])
    f = {x.id: x for x in garment.factors}
    assert (f["cotton"].indicator, f["cotton"].when_up) == ("com_cotton", "bad")
    assert (f["us_demand"].indicator, f["us_demand"].when_up) == ("us_apparel_inv_ratio", "bad") and f["us_tariff"].kind == "event"
    assert WB_COMMODITIES["com_cotton"] == "Cotton, A Index" and "com_cotton" in COMMODITY_LABELS


# The stand-ins the owner chose on 21/11/2026 (FRED, public): the US 3-2-1 crack spread for the refining margin, and US clothing stores'
# inventories to sales for apparel demand.
def test_the_us_crack_spread_is_worked_out_from_the_days_with_all_three_prices(tmp_path):
    from datetime import date

    from investment_agent.market.leading import COMMODITIES, CRACK_SERIES, MacroStore, fetch_commodities
    assert COMMODITIES["us_apparel_inv_ratio"] == "MRTSIR448USS"
    assert CRACK_SERIES == {"gasoline": "DGASNYH", "diesel": "DDFUELNYH", "brent": "DCOILBRENTEU"}
    csv = {"DGASNYH": "observation_date,DGASNYH\n2026-11-14,2.30\n2026-11-17,2.328\n",
           "DDFUELNYH": "observation_date,DDFUELNYH\n2026-11-14,4.00\n2026-11-17,4.093\n",
           "DCOILBRENTEU": "observation_date,DCOILBRENTEU\n2026-11-14,\n2026-11-17,92.94\n",
           "MRTSIR448USS": "observation_date,MRTSIR448USS\n2026-09-01,2.01\n"}
    get = lambda url: next(v for k, v in csv.items() if f"id={k}&" in url or url.endswith(f"id={k}"))  # noqa: E731
    store = MacroStore(tmp_path)
    result = fetch_commodities(store, get=get, today=date(2026, 11, 21), sleep=lambda s: None)
    assert result["crack_321_us"] == "ok" and result["us_apparel_inv_ratio"] == "ok"
    # (2 x 2.328 + 4.093) x 42 / 3 - 92.94 = 29.546; 14/11 has no Brent, so no figure for that day
    assert [(o["date"], o["value"]) for o in store.read("crack_321_us")] == [("2026-11-17", "29.55")]
    assert store.read("us_apparel_inv_ratio")[-1]["value"] == "2.01"
