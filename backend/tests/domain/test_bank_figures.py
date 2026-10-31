import pytest

from investment_agent.domain.bank_figures import UnsafeUrl, check_public_https, derive, parse_report_pages

ACB_2024 = {"group1": "447734", "group2": "7808", "group3": "1517", "group4": "1220", "group5": "2293",
            "demand_deposits": "166971", "margin_deposits": "10354", "customer_deposits": "537304.578", "car": "11.5"}


def test_derived_ratios_follow_the_owner_spreadsheet_formulas():
    d = derive(ACB_2024)
    assert d == {"npl": "0.0109", "group2_ratio": "0.0170", "casa": "0.3300", "car": "0.1150"}  # NPL 1,09%, CASA 33% as in the Excel
    assert derive({"group1": "100", "group2": "5"}) == {"npl": None, "group2_ratio": None, "casa": None, "car": None}  # groups 3–5 missing


# Text as pypdf gives it for a bank's quarterly notes: amounts in triệu đồng, this period first, prior period second.
PAGES = [
    "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT\nĐơn vị: triệu đồng\nIV Tiền gửi của khách hàng 18 537.304.578 482.702.731\nV Phát hành giấy tờ có giá 101.650.446",
    "Thuyết minh (tiếp theo)\nĐơn vị: triệu VND\n10. Tiền gửi tại các TCTD khác\nTiền gửi không kỳ hạn 25.219.753 18.504.814",
    "11. Chất lượng nợ cho vay\nĐơn vị: triệu đồng\nNợ đủ tiêu chuẩn 447.734.000 356.373.000\nNợ cần chú ý 7.808.000 3.912.000\n"
    "Nợ dưới tiêu chuẩn 1.517.000 1.433.000\nNợ nghi ngờ 1.220.000 1.015.000\nNợ có khả năng mất vốn 2.293.000 819.000",
    "18. Tiền gửi của khách hàng\nĐơn vị: triệu đồng\nTiền gửi không kỳ hạn 166.971.000 171.396.000\nTiền gửi có kỳ hạn 359.979.578 299.579.731\n"
    "Tiền gửi vốn chuyên dùng 0 0\nTiền gửi ký quỹ 10.354.000 11.727.000",
    "Tỷ lệ an toàn vốn (CAR) hợp nhất 11,50% 11,28%",
]


def test_report_pages_prefill_each_figure_with_its_page_in_billion_dong():
    out = parse_report_pages(PAGES)
    f = out["fields"]
    assert f["group1"] == {"value": "447734", "page": 3} and f["group5"] == {"value": "2293", "page": 3}
    assert f["demand_deposits"] == {"value": "166971", "page": 4}  # the customer-deposit note, not deposits at other banks
    assert f["margin_deposits"] == {"value": "10354", "page": 4}
    assert f["customer_deposits"] == {"value": "537304.578", "page": 1}
    assert f["car"] == {"value": "11.5", "page": 5}
    assert out["missing"] == []


def test_an_unknown_unit_or_an_image_only_file_fills_nothing_and_says_why():
    no_unit = ["Nợ đủ tiêu chuẩn 447.734 356.373\nNợ cần chú ý 7.808 3.912"]
    out = parse_report_pages(no_unit)
    assert "group1" not in out["fields"] and "group1" in out["missing"]
    assert any("đơn vị" in w for w in out["warnings"])
    out = parse_report_pages(["", ""])
    assert out["fields"] == {} and out["warnings"] == ["Không đọc được chữ trong file (có thể là bản scan dạng ảnh); hãy nhập tay."]


def test_only_public_https_addresses_are_fetched():
    check_public_https("https://acb.com.vn/bctc-q3-2026.pdf", resolve=lambda host: ["203.162.0.10"])
    for url, ip in (("http://acb.com.vn/a.pdf", "203.162.0.10"), ("https://localhost/a.pdf", "127.0.0.1"),
                    ("https://intranet.example/a.pdf", "192.168.1.5"), ("https://x.example/a.pdf", "169.254.169.254"), ("ftp://x/a.pdf", "1.1.1.1")):
        with pytest.raises(UnsafeUrl):
            check_public_https(url, resolve=lambda host, ip=ip: [ip])
