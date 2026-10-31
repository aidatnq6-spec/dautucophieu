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
    no_unit = ["9.1 Phân tích chất lượng nợ cho vay\nNợ đủ tiêu chuẩn 447.734 356.373\nNợ cần chú ý 7.808 3.912"]
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


# Lines as pypdf reads Techcombank's consolidated statements for 9M/2026 (public "bản tra cứu" PDF, read 31/10/2026): the unit sits
# in the column header, and deposits at other banks (note 17.1) share the page and the labels with customer deposits (note 18).
TCB = [
    "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT (tiếp theo)\n Thuyết \nminh \n30/9/2026 31/12/2025 \n triệu đồng triệu đồng \n"
    "Tiền gửi của khách hàng 18  661.390.195  618.911.535  ",
    "9.1  Phân tích chất lượng nợ cho vay \n 30/9/2026 31/12/2025 \n triệu đồng % triệu đồng % \n"
    "Nợ đủ tiêu chuẩn  795.044.933  97,70  711.706.750  98,34  \nNợ cần chú ý  7.640.722  0,94  3.852.272  0,53  \n"
    "Nợ dưới tiêu chuẩn  3.235.156  0,40  918.063  0,13  \nNợ nghi ngờ  2.462.069  0,30  1.339.119  0,18  \n"
    "Nợ có khả năng mất vốn  5.350.874  0,66  5.941.193  0,82  ",
    "17.1 Tiền gửi của các tổ chức tài chính, các TCTD khác  \n 30/9/2026 31/12/2025 \n triệu đồng triệu đồng \n"
    "Tiền gửi không kỳ hạn  1.081.527  1.199.178  \n \n18.  TIỀN GỬI CỦA KHÁCH HÀNG \n 30/9/2026 31/12/2025 \n triệu đồng triệu đồng \n"
    "Tiền gửi không kỳ hạn  205.336.117  213.415.080  \nTiền gửi có kỳ hạn  446.227.026  396.881.095  \n"
    "Tiền gửi ký quỹ  9.827.052  8.615.360  \n  661.390.195  618.911.535  \n19.  CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH",
]


def test_a_real_bank_layout_reads_units_from_column_headers_and_deposits_from_the_customer_note():
    out = parse_report_pages(TCB)
    f = out["fields"]
    assert f["group1"] == {"value": "795044.933", "page": 2} and f["group2"] == {"value": "7640.722", "page": 2}
    assert f["group5"] == {"value": "5350.874", "page": 2}
    assert f["demand_deposits"] == {"value": "205336.117", "page": 3}  # note 18, not the 1.081.527 of note 17.1 above it
    assert f["margin_deposits"] == {"value": "9827.052", "page": 3}
    assert f["customer_deposits"] == {"value": "661390.195", "page": 1}
    assert out["missing"] == ["car"]  # quarterly statements carry no CAR: left for the owner


def test_loan_groups_come_from_the_loan_quality_section_not_an_interbank_table_on_the_same_page():
    # Techcombank 1Q/2026, page 42: interbank deposit quality first, then the customer-loan quality note.
    page = ("Phân tích chất lượng dư nợ tiền gửi (không bao gồm tiền gửi không kỳ hạn) và cấp tín dụng \n triệu đồng triệu đồng \n"
            "Nợ đủ tiêu chuẩn  406.749  4.778.366 \n \n9.1  Phân tích chất lượng nợ cho vay \n 31/3/2026 31/12/2025 \n triệu đồng % triệu đồng % \n"
            "Nợ đủ tiêu chuẩn             737.972.246                       98,12                  711.706.750                       98,34  \n"
            "Nợ cần chú ý                 5.441.738                         0,72                      3.852.272                         0,53  \n"
            "Nợ dưới tiêu chuẩn                 1.391.382                         0,18                         918.063                         0,13  \n"
            "Nợ nghi ngờ                 1.395.138                         0,19                      1.339.119                         0,18  \n"
            "Nợ có khả năng mất vốn                 5.909.007                         0,79                      5.941.193                         0,82  \n"
            "             752.109.511  100,00                 723.757.397                     100,00  ")
    f = parse_report_pages([page])["fields"]
    assert f["group1"] == {"value": "737972.246", "page": 1} and f["group5"] == {"value": "5909.007", "page": 1}
    out = parse_report_pages(["Đơn vị: triệu đồng\nNợ đủ tiêu chuẩn 1.000 1\nNợ cần chú ý 2.000 1"])  # groups without a loan-quality heading
    assert "group1" not in out["fields"] and any("chất lượng nợ cho vay" in w for w in out["warnings"])


def test_car_is_read_from_a_capital_adequacy_report_taking_the_consolidated_column():
    # Techcombank "Công bố thông tin tỷ lệ an toàn vốn 30/06/2026", page 6: separate and consolidated columns, no % sign.
    page = ("Bảng 2 - Tỷ lệ an toàn vốn, Tài sản tính theo rủi ro tín dụng, Vốn yêu cầu theo từng loại rủi ro (*)  \nĐơn vị: Tỷ VND, % \n"
            " Chỉ tiêu 30/06/2026 31/12/2025 \nRiêng lẻ Hợp nhất Riêng lẻ Hợp nhất \n"
            "F Tỷ lệ vốn cấp 1 13.28  14.06  12.74 13.67 \nG Tỷ lệ an toàn vốn 12.45  14.95  11.97 14.61 ")
    assert parse_report_pages([page])["fields"]["car"] == {"value": "14.95", "page": 1}


def test_decomposed_vietnamese_text_from_a_pdf_is_normalised_before_matching():
    import unicodedata
    page = "Riêng lẻ Hợp nhất Riêng lẻ Hợp nhất \nG Tỷ lệ an toàn vốn 12.45  14.95  11.97 14.61 "
    assert parse_report_pages([unicodedata.normalize("NFD", page)])["fields"]["car"] == {"value": "14.95", "page": 1}
