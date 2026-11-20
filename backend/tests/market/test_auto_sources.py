import io
import json
import zipfile
from datetime import date

import pytest

from investment_agent.market.leading import (
    MacroError, MacroStore, fetch_auto, fetch_chain_series, parse_cafef_pmi_article, parse_cafef_pmi_links, parse_vasep_article, parse_vasep_links,
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
            "Wheat, US HRW", "Soybeans"]
_WB_COLS = "DEFGHIJKL"
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
        return WB_PAGE if "worldbank.org/en" in url else VPA if "vpa.org.vn" in url else VASEP_PAGES.get(url, VASEP_LIST)

    def get_bytes(url):
        asked.append(url)
        return PINK
    assert fetch_chain_series(store, get=get, get_bytes=get_bytes, today=date(2026, 11, 15)) == {
        "com_urea": "ok", **{k: "ok" for k in WB_COMMODITIES}, "port_container_yoy": "ok", "vn_pangasius_export_yoy": "ok"}
    assert [o["value"] for o in store.read("com_urea")] == ["407.5", "420"] and store.read("port_container_yoy")[-1]["value"] == "8.4"
    asked.clear()
    fetch_chain_series(store, get=get, get_bytes=get_bytes, today=date(2026, 11, 20))  # October is stored: the sheet is not fetched again
    assert not any("xlsx" in u or "worldbank" in u for u in asked)
    # both summaries are stored: neither is opened again, the one without a year in its title included
    assert [o["date"] for o in store.read("vn_pangasius_export_yoy")] == ["2026-07-31", "2026-08-31"]
    assert not any(u.endswith(".html") for u in asked)
    # without a bytes fetcher (tests of macro-sync), urea is not asked at all
    assert "com_urea" not in fetch_chain_series(MacroStore(tmp_path / "x"), get=get, get_bytes=None, today=date(2026, 11, 15))



def test_world_prices_come_from_the_world_bank_sheet_replacing_the_earlier_source(tmp_path):
    """FRED's copy of the IMF prices runs two to three months behind; the World Bank's sheet has last month early in the month. Its units
    differ from the IMF's, so a series is replaced whole, never joined to the older points."""
    store, asked = MacroStore(tmp_path), []
    store.upsert("com_iron_ore", [(date(2026, 8, 1), "104.2"), (date(2026, 9, 1), "105.1")], entry="auto")  # from FRED, in other units

    def get(url):
        asked.append(url)
        return WB_PAGE if "worldbank.org/en" in url else VPA if "vpa.org.vn" in url else VASEP_PAGES.get(url, VASEP_LIST)

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
    get = lambda url: WB_PAGE if "worldbank.org/en" in url else VPA if "vpa.org.vn" in url else VASEP_PAGES.get(url, VASEP_LIST)  # noqa: E731
    result = fetch_chain_series(store, get=get, get_bytes=lambda url: sheet, today=date(2026, 11, 15))
    assert result["com_iron_ore"] == "ok" and result["com_urea"] == "ok" and result["com_copper"] == "error:MacroError"
    assert store.read("com_iron_ore")[-1]["value"] == "90.8" and store.read("com_copper") == []

# Synthetic pages in the shape of VASEP's public cá tra news (11/2026); the figures are made up.
VASEP_LIST = """<a href="/san-pham-xuat-khau/ca-tra/xuat-nhap-khau/xuat-khau-ca-tra-8-thang-duy-tri-da-tang-38249.html" title="Xuất khẩu cá tra 8 tháng Duy trì đà tăng">x</a>
<a href="/san-pham-xuat-khau/ca-tra/xuat-nhap-khau/xuat-khau-ca-tra-8-thang-duy-tri-da-tang-38249.html" title="Xuất khẩu cá tra 8 tháng Duy trì đà tăng">x</a>
<a href="/san-pham-xuat-khau/ca-tra/xuat-nhap-khau/xuat-khau-ca-tra-sang-brazil-thang-8-38393.html" title="Xuất khẩu cá tra sang Brazil phục hồi mạnh trong tháng 8">x</a>
<a href="https://vasep.com.vn/san-pham-xuat-khau/ca-tra/xuat-nhap-khau/xuat-khau-ca-tra-7-thang-dau-nam-2026-37878.html" title="Xuất khẩu cá tra 7 tháng đầu năm 2026 giữ được đà tăng">x</a>
<a href="/san-pham-xuat-khau/ca-tra/xuat-nhap-khau/xuat-khau-ca-tra-6-thang-king-37001.html" title="Xuất khẩu cá tra 6 tháng tăng">x</a>"""
VASEP_BASE = "https://vasep.com.vn"


def vasep_article(body, published="2026-09-22T07:28:00+07:00"):
    return f'<script type="application/ld+json">{{"datePublished": "{published}"}}</script><div><p>{body}</p></div>'


VASEP_PAGES = {
    VASEP_BASE + "/san-pham-xuat-khau/ca-tra/xuat-nhap-khau/xuat-khau-ca-tra-8-thang-duy-tri-da-tang-38249.html": vasep_article(
        "Riêng tháng 8/2026, kim ngạch sang thị trường này đạt 60 triệu USD, tăng 18% so với cùng kỳ. "
        "Lũy kế 8 tháng đạt 1.400 triệu USD. Riêng tháng 8, xuất khẩu đạt 205 triệu USD, tăng 6%."),
    VASEP_BASE + "/san-pham-xuat-khau/ca-tra/xuat-nhap-khau/xuat-khau-ca-tra-7-thang-dau-nam-2026-37878.html": vasep_article(
        "Riêng tháng 7, xuất khẩu đạt 203 triệu USD, giảm 4,5%, cho thấy nhu cầu vẫn được duy trì.", "2026-08-20T07:00:00+07:00"),
}


def test_vasep_lists_the_monthly_export_summaries_and_skips_what_robots_txt_forbids():
    links = parse_vasep_links(VASEP_LIST)
    assert [(n, y) for n, y, _ in links] == [(8, None), (7, 2026)]  # not the Brazil piece; not a path robots.txt disallows ("king")


def test_the_month_alone_is_read_not_a_market_or_the_year_to_date():
    pages = list(VASEP_PAGES.values())
    assert parse_vasep_article(pages[0], month=8, year=None) == (date(2026, 8, 31), "6")
    assert parse_vasep_article(pages[1], month=7, year=2026) == (date(2026, 7, 31), "-4.5")
    assert parse_vasep_article(pages[0], month=9, year=None) is None
    # a December summary read in January belongs to the year before
    assert parse_vasep_article(vasep_article("Riêng tháng 12, xuất khẩu đạt 200 triệu USD, tăng 3%.", "2027-01-15T07:00:00+07:00"),
                               month=12, year=None) == (date(2026, 12, 31), "3")


# Title and sentence shapes seen on VASEP between 09/2025 and 09/2026 (the figures are made up).
def vasep_link(slug, title):
    return f'<a href="https://vasep.com.vn/san-pham-xuat-khau/ca-tra/xuat-nhap-khau/{slug}.html" title="{title}">x</a>'


VASEP_TITLES = "".join([
    vasep_link("a-1", "Trung Quốc và CPTPP là động lực cho xuất khẩu cá tra 5 tháng đầu năm"),
    vasep_link("b-2", "Xuất khẩu cá tra tháng 42026 tăng trưởng 18%, thị trường Mỹ có tín hiệu phục hồi"),
    vasep_link("c-3", "Tăng trưởng chậm, Trung Quốc vẫn là điểm tựa của cá tra Việt Nam trong tháng 32026"),
    vasep_link("d-4", "Xuất khẩu cá tra tháng đầu năm 2026 Trung Quốc tăng mạnh"),
    vasep_link("e-5", "Xuất khẩu cá tra tháng 102025 Tăng trưởng tích cực"),
    vasep_link("f-6", "Cá tra Việt Nam Vượt thách thức thương mại, xuất khẩu đạt 1,4 tỷ USD sau 8 tháng"),
    vasep_link("g-7", "Xuất khẩu cá tra sang Brazil phục hồi mạnh trong tháng 8"),
    vasep_link("h-8", "Doanh thu Vĩnh Hoàn phục hồi trong tháng 82026"),
])


def test_vasep_titles_of_every_shape_give_their_month():
    assert [(m, y) for m, y, _ in parse_vasep_links(VASEP_TITLES)] == [(5, None), (4, 2026), (3, 2026), (1, 2026), (10, 2025), (8, None)]


@pytest.mark.parametrize("sentence, month, expected", [
    ("Tháng 5/2026, xuất khẩu cá tra Việt Nam đạt 190 triệu USD, tăng 1% so với cùng kỳ năm trước.", 5, (date(2026, 5, 31), "1")),
    ("Theo số liệu Hải quan Việt Nam, xuất khẩu cá tra trong tháng 4/2026 đạt 206 triệu USD, tăng 18% so với cùng kỳ năm 2025.", 4,
     (date(2026, 4, 30), "18")),
    ("Tháng 3/2026, kim ngạch xuất khẩu cá tra của Việt Nam đạt 182 triệu USD, tăng 1% so với cùng kỳ năm 2025.", 3, (date(2026, 3, 31), "1")),
    ("Trong tháng 2/2026, xuất khẩu sang thị trường này đạt 26 triệu USD, tăng 19% so với cùng kỳ. Trong tháng 2/2026, xuất khẩu cá tra của "
     "Việt Nam đạt 119 triệu USD, giảm nhẹ 5% so với cùng kỳ năm trước.", 2, (date(2026, 2, 28), "-5")),
    ("Tháng 1/2026, xuất khẩu cá tra Việt Nam ghi nhận tín hiệu tăng trưởng tích cực ngay từ đầu năm với tổng kim ngạch đạt 212 triệu USD, "
     "tăng 59% so với cùng kỳ năm 2025.", 1, (date(2026, 1, 31), "59")),
    ("Kim ngạch xuất khẩu cá tra Việt Nam tháng 9/2025 đạt 181 triệu USD, tăng 5% so với cùng kỳ 2024.", 9, (date(2025, 9, 30), "5")),
    ("Số liệu mới nhất cho thấy, kim ngạch XK cá tra Việt Nam tháng 8/2025 vẫn tiếp tục tăng trưởng, với 200 triệu USD, tăng 5% so với "
     "tháng 8/2024.", 8, (date(2025, 8, 31), "5")),
    ("Riêng trong tháng 11, xuất khẩu cá tra đạt 195 triệu USD, tiếp tục tăng 9% so với cùng kỳ năm ngoái.", 11, (date(2026, 11, 30), "9")),
    # a market or a running total is not the month as a whole
    ("Kim ngạch xuất khẩu cá tra sang Mỹ trong tháng 9/2025 đạt 23 triệu USD, giảm 23% so với cùng kỳ năm ngoái.", 9, None),
    ("Lũy kế 4 tháng đầu năm 2026, tổng kim ngạch xuất khẩu cá tra toàn ngành đạt 720 triệu USD, tăng 17% so cùng kỳ.", 4, None),
])
def test_the_whole_months_sentence_in_its_several_wordings(sentence, month, expected):
    assert parse_vasep_article(vasep_article(sentence, "2026-12-15T07:00:00+07:00"), month=month, year=None) == expected


def test_a_short_history_reads_older_listing_pages_too(tmp_path):
    asked = []
    older = vasep_link("xuat-khau-ca-tra-thang-32026-1", "Xuất khẩu cá tra tháng 32026 tăng")

    def get(url):
        asked.append(url)
        if url.endswith("?trang=2"):
            return older
        if url.endswith("-1.html"):
            return vasep_article("Tháng 3/2026, xuất khẩu cá tra Việt Nam đạt 182 triệu USD, tăng 1% so với cùng kỳ.", "2026-04-24T07:00:00+07:00")
        return VASEP_PAGES.get(url, VASEP_LIST) if "vasep" in url else VPA
    store = MacroStore(tmp_path)
    fetch_chain_series(store, get=get, get_bytes=None, today=date(2026, 11, 15))
    assert [o["date"] for o in store.read("vn_pangasius_export_yoy")] == ["2026-03-31", "2026-07-31", "2026-08-31"]
    assert any(u.endswith("?trang=2") for u in asked)
    store.upsert("vn_pangasius_export_yoy", [(date(2025, m, 28), "1") for m in range(1, 4)], entry="auto")
    asked.clear()
    fetch_chain_series(store, get=get, get_bytes=None, today=date(2026, 11, 15))
    assert not any("?trang=" in u for u in asked)  # six months or more stored: the first page is enough
