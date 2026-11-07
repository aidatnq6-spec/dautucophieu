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


def test_a_first_number_not_written_the_vietnamese_way_leaves_the_line_without_a_candidate_instead_of_taking_a_later_one():
    pages = ["HRC, and steel billets reached 3.5 million tonnes, up 35% year-on-year.", "Thép xây dựng 1,234,567 tấn, tăng 12%",
             "Ống thép 12.5% so với 2025, đạt 300 tấn"]
    out = propose_values(pages, ["HRC", "Thép xây dựng", "Ống thép"])
    assert out["values"] == {} and out["missing"] == ["HRC", "Thép xây dựng", "Ống thép"]


def test_digits_glued_to_letters_are_words_not_numbers():
    out = propose_values(["Ống thép quý Q3 đạt 228.000 tấn", "steel pipes, up l3%, while galvanized"], ["Ống thép", "steel pipe"])
    assert [v["value"] for v in out["values"]["Ống thép"]] == ["228000"] and out["missing"] == ["steel pipe"]


GARBLED_FONT = "S/A.hookN LƯ/Ohorn.dotblNG HRC N/Ocir.dotblI /dcroat062/I.dotblA /P016/H008/Aacute033 HRC 92"
GARBLED_OCR = "v6i qu!' 2 vit ttutg 54o/o so v6i qtty. Th6p cuQn ciin n6ng (HRC) tl6ng g6p sdn 6 th6ng, ch6t luqng ph6i th6p HRC dqt 5,47"


def test_pages_whose_text_is_broken_give_no_candidates_and_are_named_in_a_warning():
    out = propose_values([GARBLED_FONT, "HRC: 512.000 tấn", GARBLED_OCR], ["HRC"])
    assert [(v["value"], v["page"]) for v in out["values"]["HRC"]] == [("512000", 2)]
    assert out["warnings"] == ["Chữ ở trang 1, 3 bị lỗi phông hoặc nhận dạng kém: không lấy số từ các trang này, hãy nhập tay."]


def test_ordinary_text_with_codes_units_and_dates_is_not_taken_for_broken_text():
    page = "Quý Q3/2026 HRC đạt 2.000.000 tấn, công suất 8,6 triệu tấn/năm; phát thải CO2 giảm; nhóm VN30; tỷ lệ 54%."
    out = propose_values([page], ["HRC"])
    assert out["values"]["HRC"][0]["value"] == "2000000" and out["warnings"] == []
