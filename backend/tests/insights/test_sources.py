import json
from datetime import date

from investment_agent.insights.sources import ReportRef, discover_acbs, discover_worldbank, ssi_titles

ACBS_LIST = """<a href="/trung-tam-phan-tich/chi-tiet/cap-nhat-vi-mo-thang-10-2026">Cập nhật vĩ mô tháng 10/2026</a>
<a href="https://acbs.com.vn/trung-tam-phan-tich/chi-tiet/chien-luoc-q4-2026">Chiến lược Q4/2026</a>
<a href="/trung-tam-phan-tich/chi-tiet/bao-cao-etf-du-bao-danh-muc-vndiamond-q3-2026">ETF</a>
<a href="/trung-tam-phan-tich/chi-tiet/cap-nhat-vi-mo-thang-10-2026">dup</a>"""
ACBS_DETAIL = {
    "cap-nhat-vi-mo-thang-10-2026": '<h1 class="x">Cập nhật Vĩ mô – tháng 10/2026: TĂNG TRƯỞNG</h1>'
                                    '<a href="https://acbs.com.vn/acbsmedia/2026/10/202610_MacroUpdate_VN_Final.pdf">Tải</a>',
    "bao-cao-etf-du-bao-danh-muc-vndiamond-q3-2026": '<a href="https://acbs.com.vn/acbsmedia/2026/10/ETF.pdf">Tải</a>',
    "chien-luoc-q4-2026": "<p>no file</p>",
}


def acbs_get(url):
    if url.endswith("bao-cao-tong-quan"):
        return ACBS_LIST
    return ACBS_DETAIL[url.rsplit("/", 1)[-1]]


def test_acbs_finds_new_reports_with_a_pdf_titles_them_from_the_detail_page_and_skips_etf_reports():
    refs = discover_acbs(acbs_get, since=date(2026, 8, 27))
    assert refs == [ReportRef("acbs", "cap-nhat-vi-mo-thang-10-2026", "Cập nhật Vĩ mô – tháng 10/2026: TĂNG TRƯỞNG",
                              "https://acbs.com.vn/trung-tam-phan-tich/chi-tiet/cap-nhat-vi-mo-thang-10-2026",
                              "https://acbs.com.vn/acbsmedia/2026/10/202610_MacroUpdate_VN_Final.pdf", date(2026, 10, 1))]
    assert discover_acbs(acbs_get, since=date(2026, 11, 1)) == []  # older than the window


WB = json.dumps({"documents": {
    "D1": {"docdt": "2026-09-30T00:00:00Z", "display_title": "Viet Nam Macro Monitoring", "docty": "Brief", "pdfurl": "http://documents.worldbank.org/x.pdf"},
    "D2": {"docdt": "2026-09-29T00:00:00Z", "display_title": "Procurement Plan", "docty": "Procurement Plan", "pdfurl": "http://d/y.pdf"},
    "D3": {"docdt": "2025-03-11T00:00:00Z", "display_title": "Taking Stock March 2025", "docty": "Report", "pdfurl": "http://d/z.pdf"},
    "facets": {}}})


def test_world_bank_keeps_recent_macro_reports_only():
    refs = discover_worldbank(lambda url: WB, since=date(2026, 8, 27))
    assert [(r.ref_id, r.published) for r in refs] == [("D1", date(2026, 9, 30))]


SSI = """<div class="chart__content__item"><div class="chart__content__item__desc"><a class="titlePost" href="javascript:void(0)">
 Cập nhật dòng vốn toàn cầu Tháng 8/2025 </a><div>tóm tắt</div></div><div class="chart__content__item__time"><p><span>10/09/2025</span></p>
<a href="https://www.ssi.com.vn/analysis-center/report/download/cap-nhat-dong-von-thang-82025"> Tải xuống </a></div></div>
<div class="chart__content__item"><div class="chart__content__item__desc"><a class="titlePost" href="javascript:void(0)"> Báo cáo chiến lược tháng 9/2026: Ra khơi </a>
</div><div class="chart__content__item__time"><p><span>05/09/2026</span></p>
<a href="https://www.ssi.com.vn/analysis-center/report/download/bao-cao-chien-luoc-thang-92026-ra-khoi"> Tải xuống </a></div></div>"""


def test_ssi_titles_are_listed_newest_first_without_downloads():
    titles = ssi_titles(lambda url: SSI, limit=5)
    assert titles[0] == {"title": "Báo cáo chiến lược tháng 9/2026: Ra khơi", "kind": "vĩ mô", "date": "2026-09-05",
                         "url": "https://www.ssi.com.vn/analysis-center/report/download/bao-cao-chien-luoc-thang-92026-ra-khoi"}
    assert titles[1]["title"] == "Cập nhật dòng vốn toàn cầu Tháng 8/2025"
    assert len(titles) == 2  # same links on every page are listed once


def test_acbs_does_not_refetch_detail_pages_of_known_reports():
    fetched = []
    get = lambda url: fetched.append(url) or acbs_get(url)
    assert discover_acbs(get, since=date(2026, 8, 27), known=lambda slug: slug == "cap-nhat-vi-mo-thang-10-2026") == []
    assert not any("cap-nhat-vi-mo" in u for u in fetched)


def test_very_long_acbs_slugs_get_a_short_stable_id():
    """26/10/2026: a 140-character ACBS slug made the store reject the id and the whole ACBS discovery came back empty."""
    from investment_agent.insights.store import _ID
    slug = "cap-nhat-nhanh-kinh-te-vi-mo-ngay-17-09-2026-fed-tang-lai-suat-25-diem-co-ban-fomc-van-de-ngo-it-nhat-mot-lan-tang-them-trong-nam-2026"
    listing = f'<a href="/trung-tam-phan-tich/chi-tiet/{slug}">x</a>'
    detail = '<h1>Fed</h1><a href="https://acbs.com.vn/acbsmedia/2026/09/Fed.pdf">pdf</a>'
    get = lambda url: listing if url.endswith("bao-cao-tong-quan") else detail
    seen = []
    refs = discover_acbs(get, since=date(2026, 8, 27), known=lambda ref_id: seen.append(ref_id) or False)
    assert len(refs) == 1 and _ID.fullmatch(refs[0].ref_id) and len(refs[0].ref_id) <= 120
    assert refs[0].ref_id == discover_acbs(get, since=date(2026, 8, 27))[0].ref_id  # stable across runs
    assert seen == [refs[0].ref_id]  # 'known' is asked with the same safe id the store uses
