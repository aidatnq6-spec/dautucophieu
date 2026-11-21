import io
import json
import zipfile
from datetime import date

import pytest

from investment_agent.market.leading import (
    MacroError, MacroStore, fetch_auto, fetch_chain_series, parse_cafef_pmi_article, parse_cafef_pmi_links,
    parse_vpa_container, parse_wb_link, parse_wb_monthly, WB_COMMODITIES, WB_COMMODITY_PAGE,
)

# Synthetic pages in the shape of cafef.vn's PMI topic page and articles (11/2026); the figures are made up.
TOPIC = """<a href="/pmi-viet-nam-tang-nhe-trong-thang-10-1882611.chn" title="PMI ngành sản xuất của Việt Nam tăng nhẹ trong tháng 10, vì sao?">x</a>
<a href="/pmi-viet-nam-tang-nhe-trong-thang-10-1882611.chn" title="PMI ngành sản xuất của Việt Nam tăng nhẹ trong tháng 10, vì sao?">x</a>
<a href="/pmi-my-thang-10-188.chn" title="PMI ngành sản xuất Mỹ tháng 10 và Việt Nam">x</a>
<a href="/pmi-viet-nam-thang-9-2026-188.chn" title="PMI ngành sản xuất Việt Nam tháng 9/2026 giảm">x</a>
<a href="/khac-188.chn" title="Giá vàng hôm nay">x</a>"""


def article(lead, published="2026-11-02T09:22:00"):
    return f'<script type="application/ld+json">{{"datePublished": "{published}"}}</script><h1>t</h1><p>{lead}</p><p>Đoạn sau 49,0 điểm trong tháng 1.</p>'


def test_the_topic_page_lists_vietnam_pmi_articles_by_month_once():
    assert parse_cafef_pmi_links(TOPIC) == [(10, None, "/pmi-viet-nam-tang-nhe-trong-thang-10-1882611.chn"), (9, 2026, "/pmi-viet-nam-thang-9-2026-188.chn")]
    # CafeF's article number starts 188 then the day it was published (yymmdd): the year follows without opening the article
    dated = '<a href="/pmi-viet-nam-thang-12-188270102093016793.chn" title="PMI Việt Nam tháng 12 tăng">x</a>' \
            '<a href="/pmi-viet-nam-thang-11-188261202093016793.chn" title="PMI Việt Nam tháng 11 tăng">x</a>'
    assert [(m, y) for m, y, _ in parse_cafef_pmi_links(dated)] == [(12, 2026), (11, 2026)]


def test_the_article_figure_must_name_the_titles_month():
    lead = "Theo S&P Global, Chỉ số Nhà quản trị mua hàng (PMI) ngành sản xuất Việt Nam đạt 50,7 điểm trong tháng 10/2026, tăng từ mức 50,1 điểm của tháng 9."
    assert parse_cafef_pmi_article(article(lead), month=10, year=None) == (date(2026, 10, 31), "50.7")
    assert parse_cafef_pmi_article(article("PMI Việt Nam giảm."), month=10, year=None) is None
    assert parse_cafef_pmi_article(article("PMI đạt 50,7 điểm trong tháng 12", "2027-01-02T09:00:00"), month=12, year=None) == (date(2026, 12, 31), "50.7")


def test_only_months_not_stored_are_opened_and_a_short_history_takes_fred_once(tmp_path):
    store = MacroStore(tmp_path)
    store.upsert("vn_pmi", [(date(2026, 9, 30), "49.9")], entry="manual")
    pages = {"https://cafef.vn/pmi.html": TOPIC,
             "https://cafef.vn/pmi-viet-nam-tang-nhe-trong-thang-10-1882611.chn": article("PMI Việt Nam đạt 50,7 điểm trong tháng 10/2026.")}
    asked = []

    def get(url):
        asked.append(url)
        if "fredgraph" in url:
            return "observation_date,DCOILBRENTEU\n2026-11-10,90.16\n2026-11-11,92.14\n"
        if "oilprice" in url:
            return "<tr data-name='Brent-Crude'><td class='last_price' data-price='95.84'></td><td data-timestamp='1763064000'></td></tr>"
        return pages[url]
    ind = [{"id": "vn_pmi", "rule": "pmi", "source": {"kind": "cafef_pmi"}},
           {"id": "brent", "rule": "up", "source": {"kind": "fred", "series": "X", "history": {"kind": "fred", "series": "DCOILBRENTEU"}}}]
    fetch_auto(ind, store, get=lambda u: get(u) if "id=X" not in u else "observation_date,X\n2026-11-13,95.84\n", today=date(2026, 11, 15), sleep=lambda s: None)
    assert [(o["date"], o["value"], o["entry"]) for o in store.read("vn_pmi")] == [("2026-09-30", "49.9", "manual"), ("2026-10-31", "50.7", "auto")]
    assert not any("thang-9-2026" in u for u in asked)  # September is stored: its article is not opened
    assert [o["date"] for o in store.read("brent")] == ["2026-11-10", "2026-11-11", "2026-11-13"]
    asked.clear()
    store.upsert("brent", [(date(2025, 1, d), "80") for d in range(1, 29)] + [(date(2025, 2, d), "80") for d in range(1, 29)] + [(date(2025, 3, 1), "80")], entry="auto")
    fetch_auto(ind[1:], store, get=lambda u: get(u) if "id=X" not in u else "observation_date,X\n2026-11-14,96\n", today=date(2026, 11, 15), sleep=lambda s: None)
    assert not any("DCOILBRENTEU" in u for u in asked)  # 60 points or more: FRED's history is not asked again


# A minimal workbook in the shape of the World Bank's CMO-Historical-Data-Monthly.xlsx (11/2026); the figures are made up.
def pink_sheet(rows):
    strings, cells_xml = [], []
    for n, row in enumerate(rows, start=1):
        cells = []
        for col, value in row.items():
            if isinstance(value, str):
                strings.append(value)
                cells.append(f'<c r="{col}{n}" t="s"><v>{len(strings) - 1}</v></c>')
            else:
                cells.append(f'<c r="{col}{n}"><v>{value}</v></c>')
        cells_xml.append(f'<row r="{n}">{"".join(cells)}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook {ns} xmlns:r="{rel}"><sheets><sheet name="Mismatch Details" sheetId="1" r:id="rId1"/>'
                                      f'<sheet name="Monthly Prices" sheetId="2" r:id="rId2"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", f'<sst {ns}>' + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>")
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet {ns}><sheetData><row r="1"><c r="A1"><v>1</v></c></row></sheetData></worksheet>')
        z.writestr("xl/worksheets/sheet2.xml", f'<worksheet {ns}><sheetData>{"".join(cells_xml)}</sheetData></worksheet>')
    return buf.getvalue()


# Brent, urea, then the world prices Chuỗi giá trị reads (columns D onward, as the sheet names them)
WB_NAMES = ["Iron ore, cfr spot", "Coal, Australian", "Rubber, RSS3", "Sugar, world", "Liquefied natural gas, Japan", "Aluminum", "Copper",
            "Wheat, US HRW", "Soybeans", "Cotton, A Index"]
_WB_COLS = "DEFGHIJKLM"
PINK = pink_sheet([{"A": "World Bank Commodity Price Data (The Pink Sheet)"}, {"B": "Crude oil, Brent", "C": "Urea ", **dict(zip(_WB_COLS, WB_NAMES))},
                   {"B": "($/bbl)", "C": "($/mt)"},
                   {"A": "2026M08", "B": 70.1, "C": "…", **{c: 99 for c in _WB_COLS}}, {"A": "2026M09", "B": 71, "C": 407.5, **{c: 100 for c in _WB_COLS}},
                   {"A": "2026M10", "B": 72, "C": 420, **{c: 90.8 for c in _WB_COLS}}])
WB_PAGE = '<a href="https://thedocs.worldbank.org/en/doc/abc-0050012026/related/CMO-Historical-Data-Annual.xlsx">Annual</a>' \
          '<a href="https://thedocs.worldbank.org/en/doc/abc-0050012026/related/CMO-Historical-Data-Monthly.xlsx">Monthly prices</a>'
VPA = json.dumps([{"date": "2026-11-13T10:00:00", "title": {"rendered": "OCTOBER 2026 CONTAINER THROUGHPUT REACHES 2.70 MILLION TEU, UP 8.4% YEAR ON YEAR"}},
                  {"date": "2026-10-29T10:00:00", "title": {"rendered": "VPA INTRODUCES A NEW ANALYTICAL REPORT ON VIETNAM&#8217;S CONTAINER THROUGHPUT"}},
                  {"date": "2026-10-12T10:00:00", "title": {"rendered": "September 2026 container throughput reaches 2.5 million TEU, down 1.2% year-on-year"}}])


def test_the_world_banks_monthly_sheet_gives_urea_by_month_and_skips_blanks():
    assert parse_wb_link(WB_PAGE).endswith("/CMO-Historical-Data-Monthly.xlsx")
    assert parse_wb_monthly(PINK, column="Urea") == [(date(2026, 9, 1), "407.5"), (date(2026, 10, 1), "420")]
    with pytest.raises(MacroError):
        parse_wb_monthly(PINK, column="Potash")


def test_vpa_titles_give_container_throughput_against_a_year_before():
    assert parse_vpa_container(VPA) == [(date(2026, 9, 30), "-1.2"), (date(2026, 10, 31), "8.4")]


def test_urea_is_asked_only_when_last_months_price_is_missing(tmp_path):
    store, asked = MacroStore(tmp_path), []

    def get(url):
        asked.append(url)
        return WB_PAGE if "worldbank.org/en" in url else VPA if "vpa.org.vn" in url else ""

    def get_bytes(url):
        asked.append(url)
        return PINK
    assert fetch_chain_series(store, get=get, get_bytes=get_bytes, today=date(2026, 11, 15)) == {
        "com_urea": "ok", **{k: "ok" for k in WB_COMMODITIES}, "port_container_yoy": "ok"}
    assert [o["value"] for o in store.read("com_urea")] == ["407.5", "420"] and store.read("port_container_yoy")[-1]["value"] == "8.4"
    asked.clear()
    fetch_chain_series(store, get=get, get_bytes=get_bytes, today=date(2026, 11, 20))  # October is stored: the sheet is not fetched again
    assert not any("xlsx" in u or "worldbank" in u for u in asked)
    # without a bytes fetcher (tests of macro-sync), urea is not asked at all
    assert "com_urea" not in fetch_chain_series(MacroStore(tmp_path / "x"), get=get, get_bytes=None, today=date(2026, 11, 15))



def test_world_prices_come_from_the_world_bank_sheet_replacing_the_earlier_source(tmp_path):
    """FRED's copy of the IMF prices runs two to three months behind; the World Bank's sheet has last month early in the month. Its units
    differ from the IMF's, so a series is replaced whole, never joined to the older points."""
    store, asked = MacroStore(tmp_path), []
    store.upsert("com_iron_ore", [(date(2026, 8, 1), "104.2"), (date(2026, 9, 1), "105.1")], entry="auto")  # from FRED, in other units

    def get(url):
        asked.append(url)
        return WB_PAGE if "worldbank.org/en" in url else VPA if "vpa.org.vn" in url else ""

    def get_bytes(url):
        asked.append(url)
        return PINK
    assert WB_COMMODITIES["com_iron_ore"] == "Iron ore, cfr spot" and "com_shrimp" not in WB_COMMODITIES  # the sheet dropped shrimp in 2023
    result = fetch_chain_series(store, get=get, get_bytes=get_bytes, today=date(2026, 11, 15))
    assert all(result[k] == "ok" for k in WB_COMMODITIES)
    iron = store.read("com_iron_ore")
    assert [(o["date"], o["value"]) for o in iron] == [("2026-08-01", "99"), ("2026-09-01", "100"), ("2026-10-01", "90.8")]
    assert all(o["source_url"] == WB_COMMODITY_PAGE for o in iron)
    asked.clear()
    fetch_chain_series(store, get=get, get_bytes=get_bytes, today=date(2026, 11, 28))  # October is stored for every price: not asked again
    assert not any("xlsx" in u or "worldbank" in u for u in asked)
    store.upsert("com_rubber", [(date(2026, 7, 1), "1.5")], entry="auto")  # a point left from the earlier source asks for the sheet again
    fetch_chain_series(store, get=get, get_bytes=get_bytes, today=date(2026, 11, 28))
    assert [o["date"] for o in store.read("com_rubber")] == ["2026-08-01", "2026-09-01", "2026-10-01"]


def test_a_price_missing_from_the_sheet_is_reported_and_the_others_still_update(tmp_path):
    store = MacroStore(tmp_path)
    sheet = pink_sheet([{"B": "Urea ", "C": "Iron ore, cfr spot"}, {"A": "2026M10", "B": 420, "C": 90.8}])
    get = lambda url: WB_PAGE if "worldbank.org/en" in url else VPA if "vpa.org.vn" in url else ""  # noqa: E731
    result = fetch_chain_series(store, get=get, get_bytes=lambda url: sheet, today=date(2026, 11, 15))
    assert result["com_iron_ore"] == "ok" and result["com_urea"] == "ok" and result["com_copper"] == "error:MacroError"
    assert store.read("com_iron_ore")[-1]["value"] == "90.8" and store.read("com_copper") == []
