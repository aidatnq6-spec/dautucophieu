import json
from datetime import date

from investment_agent.insights.sources import ReportRef, discover_acbs, discover_worldbank, ssi_titles

ACBS_LIST = """<a href="/trung-tam-phan-tich/chi-tiet/cap-nhat-vi-mo-thang-10-2026">Cập nhật vĩ mô tháng 10/2026</a>
<a href="https://acbs.com.vn/trung-tam-phan-tich/chi-tiet/chien-luoc-q4-2026">Chiến lược Q4/2026</a>
<a href="/trung-tam-phan-tich/chi-tiet/cap-nhat-vi-mo-thang-10-2026">dup</a>"""
ACBS_DETAIL = {
    "cap-nhat-vi-mo-thang-10-2026": '<a href="https://acbs.com.vn/acbsmedia/2026/10/202610_MacroUpdate_VN_Final.pdf">Tải</a>',
    "chien-luoc-q4-2026": "<p>no file</p>",
}


def acbs_get(url):
    if url.endswith("bao-cao-tong-quan"):
        return ACBS_LIST
    return ACBS_DETAIL[url.rsplit("/", 1)[-1]]


def test_acbs_finds_new_reports_with_a_pdf_and_dates_them_from_the_media_path():
    refs = discover_acbs(acbs_get, since=date(2026, 8, 27))
    assert refs == [ReportRef("acbs", "cap-nhat-vi-mo-thang-10-2026", "Cập nhật vĩ mô tháng 10/2026",
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


SSI = """<a href="/analysis-center/report/download/bao-cao-chien-luoc-thang-92026-ra-khoi">Báo cáo chiến lược tháng 9/2026: Ra khơi</a>
<a href="/analysis-center/report/download/cap-nhat-nganh-ngan-hang-tam-diem-lai-suat"><img src="x"></a>"""


def test_ssi_titles_are_listed_without_downloads():
    titles = ssi_titles(lambda url: SSI, limit=5)
    assert titles[0] == {"title": "Báo cáo chiến lược tháng 9/2026: Ra khơi", "kind": "vĩ mô",
                         "url": "https://www.ssi.com.vn/analysis-center/report/download/bao-cao-chien-luoc-thang-92026-ra-khoi"}
    assert titles[1]["title"] == "Cap nhat nganh ngan hang tam diem lai suat"  # no anchor text: humanised slug
    assert len(titles) == 2  # same links on every page are listed once
