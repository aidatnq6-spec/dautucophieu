from io import BytesIO

from pypdf import PdfWriter

from investment_agent.insights.ocr import needs_ocr, with_ocr

TEXT = "Ngân hàng Thương mại Cổ phần Quân đội — báo cáo tình hình tài chính hợp nhất tại ngày 30 tháng 09 năm 2026, đơn vị triệu đồng"


def _blank_pdf(pages: int) -> bytes:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=200)
    out = BytesIO()
    w.write(out)
    return out.getvalue()


def test_a_page_needs_ocr_when_it_has_no_vietnamese_text_layer_or_a_garbled_one():
    assert needs_ocr("") and needs_ocr("   \n")
    assert needs_ocr("Ngan hang ThU'<>'ng m�i C6 ph&n Quan d9i B02a/TCTD-HN 30/09/2026")  # a scan's broken font layer
    assert not needs_ocr(TEXT)


def test_only_image_pages_are_read_by_ocr_drawn_as_greyscale_images_on_this_machine():
    seen = []

    def read(image: bytes) -> str:
        seen.append(image[:2])
        return "Nợ đủ tiêu chuẩn 1.000"
    pages, ocr, notes = with_ocr(_blank_pdf(3), [TEXT, "", ""], read=read)
    assert pages == [TEXT, "Nợ đủ tiêu chuẩn 1.000", "Nợ đủ tiêu chuẩn 1.000"] and ocr == frozenset({1, 2})
    assert seen == [b"P5", b"P5"] and notes == []  # a PGM image each, piped to the reader: no file, nothing sent anywhere


def test_without_tesseract_the_image_pages_stay_empty_and_the_owner_is_told_why():
    pages, ocr, notes = with_ocr(_blank_pdf(2), ["", ""], read=None)
    assert pages == ["", ""] and ocr == frozenset()
    assert len(notes) == 1 and "Tesseract" in notes[0] and "2 trang" in notes[0]


def test_a_text_pdf_is_not_drawn_or_read_at_all():
    def read(image: bytes) -> str:
        raise AssertionError("no OCR for a text page")
    assert with_ocr(b"not even a pdf", [TEXT], read=read) == ([TEXT], frozenset(), [])


def test_ocr_stops_at_its_page_cap_and_says_so():
    pages, ocr, notes = with_ocr(_blank_pdf(3), ["", "", ""], read=lambda image: "chữ đọc được", max_pages=2)
    assert ocr == frozenset({0, 1}) and pages[2] == ""
    assert any("2/3" in n for n in notes)
