import json
from datetime import datetime, timezone

from investment_agent.market.insider_deals import InsiderStore, insider_deals

NOW = datetime(2026, 10, 31, tzinfo=timezone.utc)


def _row(date, kind, shares, title, code="ACB", url="https://dstock.vndirect.com.vn/tin-tuc/tin-tu-so/1"):
    return {"newsId": title[-3:], "tagCodes": code, "newsTitle": title, "newsDate": date, "newsSource": "HOSE", "numberOfShares": shares,
            "transType": kind, "dstockUrl": url}


PAGE = json.dumps({"data": [
    _row("2026-06-18", "Mua", 15746000.0, "ACB: Báo cáo về thay đổi sở hữu của cổ đông lớn Nguyễn Thiên Hương Jenny và NCLQ"),
    _row("2026-02-12", "Bán", 2219000.0, "ACB: Báo cáo kết quả giao dịch cổ phiếu của người có liên quan đến Người nội bộ Đặng Thu Hà"),
    _row("2026-01-30", "Đăng kí bán", 2219000.0, "ACB: Thông báo giao dịch cổ phiếu của người có liên quan của Người nội bộ Đặng Thu Hà"),
    _row("2025-12-15", None, None, "ACB: Báo cáo kết quả giao dịch cổ phiếu của Người nội bộ Đàm Văn Tuấn"),
    _row("2024-07-02", "Mua", 6000000.0, "ACB: Báo cáo kết quả giao dịch cổ phiếu của người có liên quan đến người nội bộ Nguyễn Thị Tố Lưu"),
    _row("2026-03-01", "Mua", 5.0, "XYZ: tagged for another ticker", code="XYZ"),
    _row("2026-03-02", "Mua", 5.0, "ACB: link elsewhere", url="javascript:alert(1)"),
]})


def test_notices_are_read_once_a_day_with_a_twelve_month_tally_that_counts_what_has_no_volume(tmp_path):
    urls = []

    def get(url):
        urls.append(url)
        return PAGE
    view = insider_deals(InsiderStore(tmp_path), "ACB", get=get, now=NOW)
    assert "q=tagCodes:ACB" in urls[0] and "sort=newsDate:desc" in urls[0]
    first = view["deals"][0]
    assert first == {"date": "2026-06-18", "kind": "Mua", "shares": 15746000, "source": "HOSE",
                     "title": "Báo cáo về thay đổi sở hữu của cổ đông lớn Nguyễn Thiên Hương Jenny và NCLQ",
                     "url": "https://dstock.vndirect.com.vn/tin-tuc/tin-tu-so/1"}
    assert [d["date"] for d in view["deals"]] == ["2026-06-18", "2026-03-02", "2026-02-12", "2026-01-30", "2025-12-15", "2024-07-02"]
    assert view["deals"][1]["url"] is None  # only links to the VNDirect notice page
    # Done trades in the last 12 months; registrations are intentions, not trades; a result without kind or volume is counted apart.
    assert view["year"] == {"since": "2025-10-31", "bought": 15746005, "buy_reports": 2, "sold": 2219000, "sell_reports": 1, "without_volume": 1}
    insider_deals(InsiderStore(tmp_path), "ACB", get=get, now=datetime(2026, 10, 31, 20, tzinfo=timezone.utc))
    assert len(urls) == 1


def test_a_failing_source_shows_the_saved_copy_or_a_reason(tmp_path):
    store = InsiderStore(tmp_path)
    insider_deals(store, "ACB", get=lambda url: PAGE, now=NOW)

    def broken(url):
        raise RuntimeError("down")
    later = insider_deals(store, "ACB", get=broken, now=datetime(2026, 11, 3, tzinfo=timezone.utc))
    assert later["stale"] is True and later["deals"]
    empty = insider_deals(InsiderStore(tmp_path / "e"), "FPT", get=broken, now=NOW)
    assert empty["deals"] == [] and empty["reason"] == "Không đọc được thông báo giao dịch (nguồn VNDirect lỗi)"
