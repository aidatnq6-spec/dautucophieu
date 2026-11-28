"""Văn bản công bố (docs/superpowers/specs/2026-11-28-van-ban-cong-bo-design.md): the pure parts."""

from investment_agent.market.filings import FilingStore, classify, doc_id, is_parent_only, label_date, links_on_page, snippets


def test_parent_only_statements_are_told_apart_from_consolidated_ones():
    assert is_parent_only("BCTC Công ty Mẹ Q2.2026 (29/07/2026)") and is_parent_only("Báo cáo tài chính riêng quý 3/2026")
    assert not is_parent_only("Báo cáo tài chính hợp nhất Công ty mẹ và các công ty con quý 2/2026")
    assert not is_parent_only("BCTC Hợp nhất Q2.2026")

PAGE = """<ul>
<li><a href="/wp-content/uploads/2026/07/20260729-kdh-bctc-hop-nhat-q22026.pdf"><span>BCTC Hợp nhất Q2.2026 +
 Giải trình trong TM</span> (29/07/2026)</a></li>
<li><a href="https://cdn.example.vn/2026/07/20260729-kdh-bctc-cong-ty-me-q22026.pdf">BCTC Công ty Mẹ Q2.2026 (29/07/2026)</a></li>
<li><a href="/gioi-thieu">Giới thiệu</a></li>
</ul>"""


def test_links_are_absolute_pdf_links_with_their_labels():
    links = links_on_page(PAGE, "https://www.example.vn/co-dong/bao-cao-tai-chinh")
    assert links == [
        {"url": "https://www.example.vn/wp-content/uploads/2026/07/20260729-kdh-bctc-hop-nhat-q22026.pdf",
         "nhan": "BCTC Hợp nhất Q2.2026 + Giải trình trong TM (29/07/2026)"},
        {"url": "https://cdn.example.vn/2026/07/20260729-kdh-bctc-cong-ty-me-q22026.pdf", "nhan": "BCTC Công ty Mẹ Q2.2026 (29/07/2026)"}]


def test_a_page_the_html_parser_cannot_read_gives_the_links_found_before_it():
    broken = '<a href="/a.pdf">BCTC Hợp nhất (29/07/2026)</a><![Ø\x15|@\x10\x7f\to0&&D'  # a site that served binary as text
    assert [x["url"] for x in links_on_page(broken, "https://www.example.vn/")] == ["https://www.example.vn/a.pdf"]


def test_consolidated_statements_and_resolutions_are_classified_parent_only_is_not():
    assert classify("BCTC Hợp nhất Q2.2026 + Giải trình trong TM (29/07/2026)") == "bctc"
    assert classify("Báo cáo tài chính hợp nhất soát xét 6 tháng năm 2026") == "bctc"
    assert classify("BCTC Công ty Mẹ Q2.2026 (29/07/2026)") == "bctc"  # kept unless a consolidated one has the same day (sync)
    assert classify("Báo cáo tài chính hợp nhất Công ty mẹ và các công ty con quý 2/2026") == "bctc"
    assert classify("Nghị quyết HĐQT thông qua BCTC kiểm toán năm 2025") == "nghi_quyet"
    assert classify("NQ HĐQT số 23 ngày 12/11/2026") == "nghi_quyet"
    assert classify("Quyết định về việc chuyển nhượng phần vốn góp tại Công ty con") == "nghi_quyet"
    assert classify("Biên bản họp và Nghị quyết ĐHĐCĐ thường niên năm 2026") == "nghi_quyet"
    assert classify("Báo cáo kết quả giao dịch cổ phiếu ESOP") is None


def test_the_date_comes_from_the_label_then_the_url():
    assert label_date("BCTC Hợp nhất Q2.2026 (29/07/2026)", "https://x.vn/a.pdf") == "2026-07-29"
    assert label_date("Quyết định chuyển nhượng", "https://x.vn/2026/06/20260605-kdh-quyet-dinh.pdf") == "2026-06-05"
    assert label_date("Quyết định chuyển nhượng", "https://x.vn/tep.pdf") is None
    assert label_date("Ngày 31/02/2026 (31/02/2026)", "https://x.vn/tep.pdf") is None  # not a real day


def test_doc_ids_are_stable_and_short():
    assert doc_id("https://x.vn/a.pdf") == doc_id("https://x.vn/a.pdf") and len(doc_id("https://x.vn/a.pdf")) == 16
    assert doc_id("https://x.vn/a.pdf") != doc_id("https://x.vn/b.pdf")


def record(ma, url, ngay, loai, pages, tieu_de="Văn bản"):
    return {"ma": ma, "id": doc_id(url), "loai": loai, "tieu_de": tieu_de, "ngay": ngay, "nguon": url, "trang_nguon": None,
            "lay_luc": "2026-11-28T13:00:00+00:00", "so_trang": len(pages), "ocr": len(pages), "trang": pages}


def test_the_store_lists_newest_first_without_page_text(tmp_path):
    store = FilingStore(tmp_path / "filings")
    store.save(record("KDH", "https://x.vn/a.pdf", "2026-04-29", "bctc", ["trang 1"]))
    store.save(record("KDH", "https://x.vn/b.pdf", "2026-07-29", "bctc", ["trang 1", "trang 2"]))
    store.save(record("KDH", "https://x.vn/c.pdf", None, "nghi_quyet", ["trang 1"]))
    listed = store.list("KDH")
    assert [r["nguon"] for r in listed] == ["https://x.vn/b.pdf", "https://x.vn/a.pdf", "https://x.vn/c.pdf"]
    assert all("trang" not in r for r in listed)
    assert store.read("KDH", doc_id("https://x.vn/b.pdf"))["trang"] == ["trang 1", "trang 2"]
    assert store.list("FPT") == []
    store.save_state({"abc": {"attempts": 1}})
    assert store.state() == {"abc": {"attempts": 1}}


def test_snippets_match_without_accents_and_say_when_there_are_more():
    page = "26.2 Doanh thu hoạt động tài chính. Lãi từ thoái vón công ty con (TM số 4.3) 896.333.984 ngàn đồng."
    docs = [record("KDH", "https://x.vn/b.pdf", "2026-07-29", "bctc", ["không có gì", page], tieu_de="BCTC Q2")]
    found, more = snippets(docs, "thoái vốn")
    assert more is False and len(found) == 1
    hit = found[0]
    assert hit["trang"] == 2 and "896.333.984" in hit["doan"] and hit["tieu_de"] == "BCTC Q2" and hit["nguon"] == "https://x.vn/b.pdf"
    assert snippets(docs, "THOÁI VỐN")[0] == found
    assert snippets(docs, "cổ tức tiền mặt") == ([], False)
    many = [record("KDH", f"https://x.vn/{i}.pdf", "2026-07-29", "bctc", ["vay ngân hàng " * 3]) for i in range(14)]
    found, more = snippets(many, "vay", limit=12)
    assert len(found) == 12 and more is True
    long = record("KDH", "https://x.vn/l.pdf", "2026-07-29", "bctc", ["x" * 2000 + " vay " + "y" * 2000])
    assert len(snippets([long], "vay", width=600)[0][0]["doan"]) <= 600


def test_a_phrase_broken_across_lines_or_in_decomposed_letters_still_matches():
    import unicodedata
    wrapped = record("KDH", "https://x.vn/w.pdf", "2026-10-30", "bctc", ["12. Thu nhập\n   khác 141.432.614"])
    assert snippets([wrapped], "thu nhập khác")[0][0]["trang"] == 1
    nfd = record("KDH", "https://x.vn/n.pdf", "2026-10-30", "bctc", [unicodedata.normalize("NFD", "Lãi từ thoái vốn công ty con")])
    assert len(snippets([nfd], "thoái vốn")[0]) == 1
