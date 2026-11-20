from datetime import date
from decimal import Decimal

import pytest

from investment_agent.market.leading import (
    DREWRY_WCI, EVN_RESERVOIRS, FAO_INDICES, MacroError, MacroStore, fetch_chain_extras, parse_drewry_wci, parse_evn_inflow, parse_fao_dairy,
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
DREWRY = """<html><head><meta name="description" content="19 Nov 2026: Drewry’s World Container Index (WCI) decreased 3% to $4,176 per 40ft container.">
</head><body>WCI</body></html>"""


def evn(flows: dict[str, str]) -> str:
    head = "<tr><td>Mực nước thượng lưu (m)</td><td>Mực nước dâng bình thường (m)</td><td>x</td><td>Lưu lượng đến hồ (m3/s)</td><td>x</td><td>x</td></tr>"
    rows = "".join(f'<tr><td>{n}<span class="s">Đồng bộ lúc: 23:50 19/11</span></td><td>20/11 00:00</td><td>119.81</td><td>120</td><td>90</td>'
                   f"<td>{q}</td><td>179</td><td>0</td><td>179</td></tr>" for n, q in flows.items())
    return f"<html><body><table>{head}{rows}</table></body></html>"


NAMES = ["Lai Châu", "Sơn La", "Hòa Bình", "Tuyên Quang", "Thác Bà", "Bản Chát", "Huội Quảng", "Trung Sơn", "Ialy", "Trị An", "Hàm Thuận"]


def test_fao_gives_the_dairy_index_by_month_and_skips_blanks():
    assert parse_fao_dairy(FAO) == [(date(2026, 9, 1), "119.1"), (date(2026, 10, 1), "117.8")]
    with pytest.raises(MacroError):
        parse_fao_dairy("Date,Food Price Index,Meat\n2026-10,1,2\n")


def test_drewry_gives_the_weeks_composite_index():
    assert parse_drewry_wci(DREWRY) == (date(2026, 11, 19), "4176")
    with pytest.raises(MacroError):
        parse_drewry_wci("<html>nothing</html>")


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
        if url == DREWRY_WCI:
            return DREWRY
        assert url.startswith(EVN_RESERVOIRS + "?td=")
        return evn(then if "/2025%20" in url else now)
    result = fetch_chain_extras(store, get=get, today=date(2026, 11, 20), sleep=lambda s: None)
    assert result == {"com_dairy": "ok", "com_container_wci": "ok", "vn_hydro_inflow_yoy": "ok"}
    assert [o["value"] for o in store.read("com_dairy")] == ["119.1", "117.8"]
    assert store.read("com_container_wci") == [{**store.read("com_container_wci")[0], "date": "2026-11-19", "value": "4176"}]
    hydro = store.read("vn_hydro_inflow_yoy")
    # the last seven days, each against the same day a year before, over the reservoirs found on both days: 1,100 against 1,000, +10%
    assert [o["date"] for o in hydro] == [f"2026-11-{d}" for d in range(14, 21)] and {o["value"] for o in hydro} == {"10.0"}
    assert any("td=20/11/2025%2000:00" in u for u in asked) and any("td=20/11/2026%2000:00" in u for u in asked)
    asked.clear()
    fetch_chain_extras(store, get=get, today=date(2026, 11, 20), sleep=lambda s: None)  # October's index, this week's WCI, every day stored
    assert asked == []
    fetch_chain_extras(store, get=get, today=date(2026, 11, 21), sleep=lambda s: None)  # a new day: only that day is read (two pages)
    assert len([u for u in asked if u.startswith(EVN_RESERVOIRS)]) == 2 and not any(u in (FAO_INDICES, DREWRY_WCI) for u in asked)


def test_too_few_reservoirs_on_both_days_is_not_stored(tmp_path):
    store = MacroStore(tmp_path)
    get = lambda url: FAO if url == FAO_INDICES else DREWRY if url == DREWRY_WCI else evn({"Lai Châu": "100"})  # noqa: E731
    result = fetch_chain_extras(store, get=get, today=date(2026, 11, 20), sleep=lambda s: None)
    assert result["vn_hydro_inflow_yoy"] == "error:MacroError" and store.read("vn_hydro_inflow_yoy") == []
    assert result["com_dairy"] == "ok"  # the other sources still update
