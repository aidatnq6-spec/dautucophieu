"""Văn bản công bố cho Claude (docs/superpowers/specs/2026-11-28-van-ban-cong-bo-design.md)."""

import pytest

from investment_agent.market.filings import FilingStore, doc_id
from investment_agent.public_tools import PublicData


def save(store, url, ngay, loai, pages, tieu_de, unread=()):
    store.save({"ma": "KDH", "id": doc_id(url), "loai": loai, "tieu_de": tieu_de, "ngay": ngay, "nguon": url,
                "trang_nguon": "https://www.example.vn/co-dong", "lay_luc": "2026-11-28T13:00:00+00:00", "so_trang": len(pages),
                "ocr": len(pages), "trang_chua_doc": list(unread), "trang": pages})


@pytest.fixture
def data(tmp_path):
    store = FilingStore(tmp_path / "filings")
    save(store, "https://x.vn/q2.pdf", "2026-07-29", "bctc",
         ["Bảng cân đối", "26.2 Doanh thu hoạt động tài chính: Lãi từ thoái vón công ty con 896.333.984"], "BCTC Hợp nhất Q2.2026")
    save(store, "https://x.vn/q3.pdf", "2026-10-30", "bctc", ["", "Vay dài hạn ngân hàng 16.125.462.490"], "BCTC Hợp nhất Q3.2026",
         unread=[1])
    save(store, "https://x.vn/qd.pdf", "2026-06-05", "nghi_quyet", ["Quyết định chuyển nhượng 51% vốn Bình Trưng Mới"], "Quyết định")
    return PublicData(tmp_path)


def test_without_a_keyword_the_tool_lists_filings_newest_first(data):
    out = data.van_ban_cong_bo("kdh")
    assert out["ma"] == "KDH" and [v["tieu_de"] for v in out["van_ban"]] == ["BCTC Hợp nhất Q3.2026", "BCTC Hợp nhất Q2.2026", "Quyết định"]
    assert all("trang" not in v for v in out["van_ban"]) and "OCR" in out["luu_y"]
    assert out["van_ban"][0]["trang_chua_doc"] == [1]  # pages OCR could not read are said, not hidden
    assert [v["tieu_de"] for v in data.van_ban_cong_bo("KDH", loai="nghi_quyet")["van_ban"]] == ["Quyết định"]
    assert [v["tieu_de"] for v in data.van_ban_cong_bo("KDH", tu_ngay="2026-07-01")["van_ban"]] == ["BCTC Hợp nhất Q3.2026", "BCTC Hợp nhất Q2.2026"]


def test_a_keyword_returns_passages_with_page_and_source(data):
    out = data.van_ban_cong_bo("KDH", tu_khoa="thoái vốn")
    assert out["tu_khoa"] == "thoái vốn" and out["con_nua"] is False and len(out["doan"]) == 1
    hit = out["doan"][0]
    assert (hit["tieu_de"], hit["ngay"], hit["loai"], hit["trang"], hit["nguon"]) == (
        "BCTC Hợp nhất Q2.2026", "2026-07-29", "bctc", 2, "https://x.vn/q2.pdf")
    assert "896.333.984" in hit["doan"]
    assert data.van_ban_cong_bo("KDH", tu_khoa="cổ tức tiền mặt")["doan"] == []


def test_a_ticker_without_filings_is_missing_with_one_reason(data):
    assert data.van_ban_cong_bo("FPT") == {"thieu": True, "ly_do": "Chưa có văn bản công bố của FPT trong kho."}
    assert data.van_ban_cong_bo("FPT", tu_khoa="vay") == {"thieu": True, "ly_do": "Chưa có văn bản công bố của FPT trong kho."}
    assert data.van_ban_cong_bo("!!") == {"thieu": True, "ly_do": "Mã không hợp lệ."}


def test_bad_type_or_date_is_missing(data):
    assert data.van_ban_cong_bo("KDH", loai="khac") == {"thieu": True, "ly_do": "loai cần là bctc hoặc nghi_quyet."}
    assert data.van_ban_cong_bo("KDH", tu_ngay="28/11/2026") == {"thieu": True, "ly_do": "Ngày không hợp lệ (cần YYYY-MM-DD)."}
