from investment_agent.domain.operating_pdf import parse_number, propose_values

PAGE = """TẬP ĐOÀN HÒA PHÁT - BẢN TIN SẢN XUẤT KINH DOANH THÁNG 10/2026
Sản lượng bán hàng thép xây dựng đạt 412.300 tấn, tăng 18% so với cùng kỳ năm 2025.
Thép cuộn cán nóng HRC: 512.000 tấn.
Ống thép: 72.150 tấn; tôn mạ 41.230,5 tấn
"""


def test_vietnamese_numbers_read_with_dots_for_thousands_and_a_comma_for_decimals():
    assert str(parse_number("412.300")) == "412300" and str(parse_number("41.230,5")) == "41230.5" and str(parse_number("18")) == "18"
    assert parse_number("abc") is None


def test_each_line_gets_the_first_number_after_its_name_with_the_page_and_the_text_around_it():
    out = propose_values([PAGE], ["Thép xây dựng", "HRC", "Ống thép", "Tôn mạ", "Phôi thép"])
    assert out["values"]["Thép xây dựng"][0] == {"value": "412300", "page": 1,
                                                  "text": "Sản lượng bán hàng thép xây dựng đạt 412.300 tấn, tăng 18% so với cùng kỳ năm 2025."}
    assert out["values"]["HRC"][0]["value"] == "512000"
    assert out["values"]["Ống thép"][0]["value"] == "72150" and out["values"]["Tôn mạ"][0]["value"] == "41230.5"
    assert out["missing"] == ["Phôi thép"] and out["warnings"] == []


def test_years_and_dates_are_not_taken_and_at_most_three_candidates_are_kept():
    pages = ["Thép xây dựng năm 2026 đạt 100 tấn", "Thép xây dựng tháng 10/2026: 200 tấn", "Thép xây dựng 300", "Thép xây dựng 400"]
    vals = propose_values(pages, ["Thép xây dựng"])["values"]["Thép xây dựng"]
    assert [v["value"] for v in vals] == ["100", "200", "300"] and [v["page"] for v in vals] == [1, 2, 3]


def test_a_scanned_pdf_without_text_says_so():
    out = propose_values(["", "  "], ["HRC"])
    assert out["values"] == {} and out["missing"] == ["HRC"] and out["warnings"] == ["PDF không có chữ (bản scan ảnh): hãy nhập tay."]
