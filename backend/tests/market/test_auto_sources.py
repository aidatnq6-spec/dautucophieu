from datetime import date

from investment_agent.market.leading import MacroStore, fetch_auto, parse_cafef_pmi_article, parse_cafef_pmi_links

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
