from datetime import date
from decimal import Decimal

import pytest

from investment_agent.market.leading import (
    EVN_RESERVOIRS, FAO_INDICES, SHFE_DAILY, SSE_INDEX, MacroError, MacroStore, fetch_chain_extras, fetch_chain_markets, parse_evn_inflow,
    parse_fao_dairy, parse_shfe_hrc, parse_sse_index,
)

# Synthetic files in the shape of the public sources (checked 20/11/2026); the figures are made up.
FAO = """\ufeffFAO Food Price Index,,,,,,,,
2014-2016=100,,,,,,,,
Date,Food Price Index,Meat,Dairy,Cereals,Oils,Sugar,,
,,,,,,,,
2026-08,133.9,129.0,,116.8,196.9,107.4,,
2026-09,135.6,127.1,119.1,122.3,198.6,113.7,,
2026-10,133.9,125.5,117.8,116.8,199.2,121.3,,
,,,,,,,,
"""


def evn(flows: dict[str, str]) -> str:
    head = "<tr><td>Mực nước thượng lưu (m)</td><td>Mực nước dâng bình thường (m)</td><td>x</td><td>Lưu lượng đến hồ (m3/s)</td><td>x</td><td>x</td></tr>"
    rows = "".join(f'<tr><td>{n}<span class="s">Đồng bộ lúc: 23:50 19/11</span></td><td>20/11 00:00</td><td>119.81</td><td>120</td><td>90</td>'
                   f"<td>{q}</td><td>179</td><td>0</td><td>179</td></tr>" for n, q in flows.items())
    return f"<html><body><table>{head}{rows}</table></body></html>"


NAMES = ["Lai Châu", "Sơn La", "Hòa Bình", "Tuyên Quang", "Thác Bà", "Bản Chát", "Huội Quảng", "Trung Sơn", "Ialy", "Trị An", "Hàm Thuận"]


def no_trading(url):
    """What SHFE answers for a day without trading: a 404 (httpx raises it from raise_for_status)."""
    import httpx
    raise httpx.HTTPStatusError("404", request=httpx.Request("GET", url), response=httpx.Response(404))


def test_fao_gives_the_dairy_index_by_month_and_skips_blanks():
    assert parse_fao_dairy(FAO) == [(date(2026, 9, 1), "119.1"), (date(2026, 10, 1), "117.8")]
    with pytest.raises(MacroError):
        parse_fao_dairy("Date,Food Price Index,Meat\n2026-10,1,2\n")


def test_evn_gives_the_inflow_of_each_reservoir_and_skips_blanks():
    page = evn({"Lai Châu": "260", "Sơn La": "1,081.5", "Hòa Bình": "-"})
    assert parse_evn_inflow(page) == {"Lai Châu": Decimal("260"), "Sơn La": Decimal("1081.5")}


def test_the_three_series_are_stored_and_asked_only_when_due(tmp_path):
    store, asked = MacroStore(tmp_path), []
    now = {n: "110" for n in NAMES}                     # 11 reservoirs: 1,210 m3/s today
    then = {**{n: "100" for n in NAMES[:-1]}, "Khác": "999"}  # a year before: 1,000 across the 10 found on both days

    def get(url):
        asked.append(url)
        if url == FAO_INDICES:
            return FAO
        assert url.startswith(EVN_RESERVOIRS + "?td=")
        return evn(then if "/2025%20" in url else now)
    result = fetch_chain_extras(store, get=get, today=date(2026, 11, 20), sleep=lambda s: None)
    assert result == {"com_dairy": "ok", "vn_hydro_inflow_yoy": "ok"}
    assert [o["value"] for o in store.read("com_dairy")] == ["119.1", "117.8"]
    hydro = store.read("vn_hydro_inflow_yoy")
    # the last seven days, each against the same day a year before, over the reservoirs found on both days: 1,100 against 1,000, +10%
    assert [o["date"] for o in hydro] == [f"2026-11-{d}" for d in range(14, 21)] and {o["value"] for o in hydro} == {"10.0"}
    assert any("td=20/11/2025%2000:00" in u for u in asked) and any("td=20/11/2026%2000:00" in u for u in asked)
    asked.clear()
    fetch_chain_extras(store, get=get, today=date(2026, 11, 20), sleep=lambda s: None)  # October's index and every day stored
    assert asked == []
    fetch_chain_extras(store, get=get, today=date(2026, 11, 21), sleep=lambda s: None)  # a new day: only that day is read (two pages)
    assert len([u for u in asked if u.startswith(EVN_RESERVOIRS)]) == 2 and FAO_INDICES not in asked


def test_too_few_reservoirs_on_both_days_is_not_stored(tmp_path):
    store = MacroStore(tmp_path)
    get = lambda url: FAO if url == FAO_INDICES else evn({"Lai Châu": "100"})  # noqa: E731
    result = fetch_chain_extras(store, get=get, today=date(2026, 11, 20), sleep=lambda s: None)
    assert result["vn_hydro_inflow_yoy"] == "error:MacroError" and store.read("vn_hydro_inflow_yoy") == []
    assert result["com_dairy"] == "ok"  # the other sources still update


# The Shanghai Shipping Exchange's public current index (en.sse.net.cn/currentIndex, no robots.txt), in its shape; the figures are made up.
def sse(item: str, current: str, last: str) -> str:
    return ('{"data":{"currentDate":"%s","lastDate":"%s","lineDataList":[{"properties":{"lineName_EN":"Comprehensive Index"},'
            '"currentContent":3503.7828,"lastContent":3572.3268,"dataItemTypeName":"%s"},{"properties":{"lineName_EN":"Europe"},'
            '"currentContent":null,"lastContent":null,"dataItemTypeName":"X_L1"}]},"status":0}') % (current, last, item)


# The Shanghai Futures Exchange's public daily data (www.shfe.com.cn, kx<date>.dat), in its shape; the figures are made up.
def shfe(*contracts: tuple[str, str, int, int]) -> str:
    rows = ",".join('{"PRODUCTID":"%s","DELIVERYMONTH":"%s","SETTLEMENTPRICE":%d,"OPENINTEREST":%d}' % c for c in contracts)
    return '{"o_curinstrument":[%s,{"PRODUCTID":"hc_f","DELIVERYMONTH":"小计","SETTLEMENTPRICE":"","OPENINTEREST":9}]}' % rows


def test_sse_gives_the_composite_this_period_and_the_one_before():
    text = sse("SCFI_T", "2026-11-20", "2026-11-13")
    assert parse_sse_index(text, "SCFI_T") == [(date(2026, 11, 13), "3572.3268"), (date(2026, 11, 20), "3503.7828")]
    with pytest.raises(MacroError):
        parse_sse_index(text, "CTFI_T")


def test_shfe_gives_the_hot_rolled_coil_contract_most_held():
    text = shfe(("hc_f", "2612", 3057, 3517), ("hc_f", "2701", 3114, 1645533), ("hc_f", "2705", 3125, 445419), ("rb_f", "2701", 2983, 9999999))
    assert parse_shfe_hrc(text) == "3114"
    with pytest.raises(MacroError):
        parse_shfe_hrc(shfe(("rb_f", "2701", 2983, 1)))


def test_freight_and_steel_are_stored_with_a_month_back_for_steel(tmp_path):
    store, asked = MacroStore(tmp_path), []
    trading = {"20261120", "20261119", "20261118", "20261117", "20261116", "20261020", "20261019"}

    def get(url):
        asked.append(url)
        if url.startswith(SSE_INDEX):
            return sse("SCFI_T", "2026-11-20", "2026-11-13") if "scfi" in url else sse("CTFI_T", "2026-11-20", "2026-11-19")
        day = url.removeprefix(SHFE_DAILY.split("{")[0]).removesuffix(".dat")
        if day not in trading:
            no_trading(url)
        return shfe(("hc_f", "2701", 3000 + int(day[-2:]), 100))
    result = fetch_chain_markets(store, get=get, today=date(2026, 11, 21), sleep=lambda s: None)  # a Saturday
    assert result == {"com_container_scfi": "ok", "com_tanker_ctfi": "ok", "com_steel_hrc": "ok"}
    assert [o["date"] for o in store.read("com_container_scfi")] == ["2026-11-13", "2026-11-20"]
    assert [o["date"] for o in store.read("com_tanker_ctfi")] == ["2026-11-19", "2026-11-20"]
    # the week's trading days, and the first trading day found a month back (20/10) so the month-long move reads at once
    assert [o["date"] for o in store.read("com_steel_hrc")] == ["2026-10-20", "2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"]
    assert not any("20261121" in u or "20261115" in u for u in asked)  # weekends are not asked
    asked.clear()
    fetch_chain_markets(store, get=get, today=date(2026, 11, 21), sleep=lambda s: None)
    assert not any(u.startswith(SHFE_DAILY.split("{")[0]) for u in asked)  # stored days and the month back are not asked again


def test_steel_takes_the_last_trading_day_of_each_of_the_last_12_quarters_once(tmp_path):
    """HRC cuối quý (owner, 23/11/2026): the year-before price the inventory check needs; a holiday steps back, at most 10 days; a quarter
    tried is not asked again, found or not; calls 2 seconds apart."""
    store, asked, slept = MacroStore(tmp_path), [], []
    # 30/09/2026 a Wednesday (traded); 30/06/2026 missing, 29/06 traded; 31/03/2026 and the 10 days before: none (left out)
    trading = {"20261120", "20261117", "20260930", "20260629", "20251231", "20250930", "20250630", "20250331", "20241231", "20240930",
               "20240628", "20240329", "20231229", "20230928", "20230630"}

    def get(url):
        asked.append(url)
        if url.startswith(SSE_INDEX):
            return sse("SCFI_T", "2026-11-20", "2026-11-13") if "scfi" in url else sse("CTFI_T", "2026-11-20", "2026-11-19")
        day = url.removeprefix(SHFE_DAILY.split("{")[0]).removesuffix(".dat")
        if day not in trading:
            no_trading(url)
        return shfe(("hc_f", "2701", 3000 + int(day[-3:]), 100))
    fetch_chain_markets(store, get=get, today=date(2026, 11, 21), sleep=slept.append)
    have = {o["date"] for o in store.read("com_steel_hrc")}
    assert {"2026-09-30", "2026-06-29", "2025-12-31", "2025-09-30", "2025-06-30", "2025-03-31", "2024-12-31", "2024-09-30", "2024-06-28",
            "2024-03-29", "2023-12-29"} <= have
    assert "2023-09-28" not in have  # Q3/2023 is the 13th quarter back: not asked
    assert not any("20260321" in u for u in asked)  # 31/03/2026 steps back at most 10 days, to 21/03
    assert 2 in slept
    asked.clear()
    fetch_chain_markets(store, get=get, today=date(2026, 11, 21), sleep=slept.append)
    days = {u.removeprefix(SHFE_DAILY.split("{")[0]).removesuffix(".dat") for u in asked if u.startswith(SHFE_DAILY.split("{")[0])}
    assert days <= {"20261116", "20261118", "20261119"}  # only the week's untraded days, as before; no quarter tried is asked again


def test_no_recent_steel_price_is_reported(tmp_path):
    def get(url):
        if url.startswith(SSE_INDEX):
            raise OSError("offline")
        raise OSError("404")
    result = fetch_chain_markets(MacroStore(tmp_path), get=get, today=date(2026, 11, 20), sleep=lambda s: None)
    assert result == {"com_container_scfi": "error:OSError", "com_tanker_ctfi": "error:OSError", "com_steel_hrc": "error:MacroError"}



def test_a_quarter_whose_days_failed_to_answer_is_tried_again_and_the_quarter_end_itself_is_taken(tmp_path):
    """Review 23/11/2026 (tồn kho): a network failure is not a holiday, so the quarter is not marked tried; a point stored earlier in the
    quarter's last ten days does not stand in for the last trading day."""
    store = MacroStore(tmp_path)
    store.upsert("com_steel_hrc", [(date(2026, 9, 24), "3100")], entry="auto")
    asked, offline = [], {"on": True}

    def get(url):
        asked.append(url)
        if url.startswith(SSE_INDEX):
            return sse("SCFI_T", "2026-11-20", "2026-11-13") if "scfi" in url else sse("CTFI_T", "2026-11-20", "2026-11-19")
        day = url.removeprefix(SHFE_DAILY.split("{")[0]).removesuffix(".dat")
        if day in ("20261120", "20261117"):
            return shfe(("hc_f", "2701", 3200, 100))
        if day.startswith("2026-06") or day.startswith("202606"):
            if offline["on"]:
                raise OSError("timed out")
            return shfe(("hc_f", "2701", 3150, 100)) if day == "20260630" else no_trading(url)
        if day == "20260930":
            return shfe(("hc_f", "2701", 3282, 100))
        no_trading(url)
    fetch_chain_markets(store, get=get, today=date(2026, 11, 21), sleep=lambda s: None)
    have = {o["date"]: o["value"] for o in store.read("com_steel_hrc")}
    assert have["2026-09-30"] == "3282"  # the quarter's last trading day, though 24/09 was stored
    assert "2026-06-30" not in have
    offline["on"] = False
    fetch_chain_markets(store, get=get, today=date(2026, 11, 21), sleep=lambda s: None)
    assert {o["date"]: o["value"] for o in store.read("com_steel_hrc")}["2026-06-30"] == "3150"  # tried again once SHFE answered


def test_the_tried_quarters_of_the_first_rules_are_not_trusted(tmp_path):
    """Review 23/11/2026 (4): the first rules marked quarters tried on a network failure or a nearby stored day; their file is not read."""
    import json as _json
    store = MacroStore(tmp_path)
    (tmp_path / "macro-state").mkdir()
    (tmp_path / "macro-state" / "shfe-hrc-quarters.json").write_text(_json.dumps({"tried": ["2026-09-30"]}), encoding="utf-8")
    asked = []

    def get(url):
        asked.append(url)
        if url.startswith(SSE_INDEX):
            return sse("SCFI_T", "2026-11-20", "2026-11-13") if "scfi" in url else sse("CTFI_T", "2026-11-20", "2026-11-19")
        day = url.removeprefix(SHFE_DAILY.split("{")[0]).removesuffix(".dat")
        if day in ("20261120", "20260930"):
            return shfe(("hc_f", "2701", 3282, 100))
        no_trading(url)
    fetch_chain_markets(store, get=get, today=date(2026, 11, 21), sleep=lambda s: None)
    assert "2026-09-30" in {o["date"] for o in store.read("com_steel_hrc")}
