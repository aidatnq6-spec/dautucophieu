import json
from datetime import date

import pytest

from investment_agent.market.providers.hose_baskets import BasketError, latest_size_baskets, parse_size_notice

VN30 = [f"A{i:02d}" for i in range(1, 31)]
MID = [f"M{i:02d}" for i in range(1, 71)]


def rows(codes, start=1):
    return "\n".join(f"{start + i} {c} CTCP {c} 1,000,000        50% 100.00%" for i, c in enumerate(codes))


def pages(vn100=None, vn30=VN30):
    vn100 = sorted(VN30 + MID) if vn100 is None else vn100
    return [f"Kỳ tháng 10/2026\nStt Mã cổ phiếu Tên Công ty\n{rows(vn30)}\nStt Cổ phiếu Tên  Công ty\n{rows(['R01', 'R02'])}\n"
            "SỞ GIAO DỊCH CHỨNG KHOÁN TP.HCM\nCẬP NHẬT THÔNG TIN CỔ PHIẾU THÀNH PHẦN CỦA CHỈ SỐ VN30\nDanh mục cổ phiếu dự phòng chỉ số VN30",
            f"Kỳ tháng 10/2026\n{rows(MID[:58])}\nCẬP NHẬT THÔNG TIN CỔ PHIẾU THÀNH PHẦN CỦA CHỈ SỐ VNMIDCAP",
            f"2\n{rows(MID[58:], 59)}\nStt Cổ phiếu Tên  Công ty\n{rows(['R03'])}\nDanh mục cổ phiếu dự phòng chỉ số VNMidcap",
            f"Kỳ tháng 10/2026\n{rows(vn100[:59])}\nCẬP NHẬT THÔNG TIN CỔ PHIẾU THÀNH PHẦN CHỈ SỐ VN100",
            f"1\n{rows(vn100[59:], 60)}",
            f"Kỳ tháng 10/2026\n{rows(['S01', 'S02'])}\nCẬP NHẬT THÔNG TIN CỔ PHIẾU THÀNH PHẦN CỦA CHỈ SỐ VNSMALLCAP"]


def test_the_size_notice_gives_vn30_and_vn100_without_the_reserve_lists():
    got = parse_size_notice(pages())
    assert got["VN30"] == VN30 and len(got["VN100"]) == 100 and got["VNMIDCAP"] == MID


def test_a_vn100_that_is_not_vn30_and_vnmidcap_or_not_a_hundred_is_refused():
    with pytest.raises(BasketError, match="VN30 và VNMidcap"):
        parse_size_notice(pages(vn100=sorted(VN30 + MID[:69] + ["ZZZ"])))
    with pytest.raises(BasketError, match="VN30 có 29 mã"):
        parse_size_notice(pages(vn30=VN30[:29]))


def test_the_latest_notice_is_found_in_the_news_of_hose_with_its_effective_day_and_its_pdf():
    news = {"data": {"list": [
        {"id": 7, "title": "HOSE: Danh mục cổ phiếu thành phần của Chỉ số VNDIAMOND kỳ tháng 10/2026", "postedDate": 1793633505, "summary": ""},
        {"id": 9, "title": "HOSE: Cập nhật danh mục cổ phiếu thành phần của Chỉ số quy mô VNAllshare  kỳ tháng 10/2026", "postedDate": 1793633505,
         "summary": "<p>... của các chỉ số quy mô VNAllshare có hiệu lực vào ngày 16/11/2026, chi tiết file đính kèm:</p>"}]}}
    files = {"data": {"list": [{"fileName": "II.2. QUY MO.pdf", "filePath": "~/Uploads/UploadDocuments/9/II.2. QUY MO.pdf"}]}}
    seen = []

    def get_text(url):
        seen.append(url)
        return json.dumps(files if "mediafiles/1/9" in url else news)

    def get_bytes(url):
        seen.append(url)
        return b"%PDF-1.7"
    got = latest_size_baskets(get_text=get_text, get_bytes=get_bytes, extract=lambda data: pages())
    assert got["notice_id"] == 9 and got["effective"] == date(2026, 11, 16) and got["period"] == "10/2026"
    assert got["groups"]["VN30"] == VN30 and len(got["groups"]["VN100"]) == 100
    assert seen[-1] == "https://staticfile.hsx.vn/Uploads/UploadDocuments/9/II.2.%20QUY%20MO.pdf"
    with pytest.raises(BasketError, match="chưa thấy"):
        latest_size_baskets(get_text=lambda u: json.dumps({"data": {"list": []}}), get_bytes=get_bytes, extract=lambda d: pages())
