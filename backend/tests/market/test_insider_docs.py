"""Số lượng giao dịch nội bộ đọc từ văn bản HOSE (docs/superpowers/specs/2026-11-26-so-luong-tu-van-ban-hose-design.md)."""

import json
from datetime import datetime, timezone

from investment_agent.market.insider_deals import InsiderStore, insider_deals
from investment_agent.market.insider_docs import (DocStore, fill_from_docs, news_id, parse_report, read_notice,
                                                  sync_insider_docs)

NOW = datetime(2026, 11, 26, 13, tzinfo=timezone.utc)

# What OCR gives for an insider's result report: noisy accents, the English half after a slash, two "after" figures.
INSIDER = """BÁO CÁO KẾT QUÁ GIAO DỊCH CÔ PHIẾU CỦA NGƯỜI NỘI BỘ
- Số lượng, tỷ lệ cổ phiếu mà người nội bộ đang nắm giữ/Xmber of shares held: 2.425.159 cô phiêu/shares, chiêm 0,22%
5. Số lượng, tỷ lệ cổ phiếu nắm giữ trước khi thực hiện giao dịch/Àzznber, ownership percenfage oƒ
| shares held before the transacHion: {before} cô phiều/shares, chiêm 1,84% vôn điều
6. Số lượng cổ phiếu đăng ký mua/Xzber of shares registered to puychase:
- Loại giao dịch đăng ký/7ype oƒ transacftion registered: Mua/Purchase
| - Số lượng cổ phiếu đăng ký giao dịch/ðVu/mber oƒ shares registered for trading: 650.000 cổ
7. Số lượng cổ phiếu đã giao dịch/W/nber oƒ shares being traded:
- Loại giao dịch đã thực hiện/73/5e oƒ 1ranSaction executed: {kind}/Purchase
- Số lượng cổ phiếu đã giao dịch/Xz?ber: of shares íraded: {traded} cổ phiếu/s#:ares
8. Giá trị đã giao dịch (tính theo mệnh giá): 6.500.000.000 đồông/VND 6,500,000,000
9 Số lượng, tỷ lệ cổ phiếu nắm giữ sau khi thực hiện giao dịch của người thực hiện giao dịch/Xz/nber,
Ownership perceniage oƒ shares afer the transaction:
{after} cô phiêu/s#ares, chiêm 1,90% vôn điều lệ
Số lượng, tỷ lệ cổ phiếu nắm giữ sau khi thực hiện giao dịch của người thực hiện giao dịch và
người có liên quan: 149.825.932 cô phiêu/sbares, chiêm 13,35% vôn điều lệ
11. Phương thức giao dịch/Ä/erhod oƒ itransacfion: {method}
12. Thời gian thực hiện giao dịch/ 7rading íizne: 06/10/2026
"""

# A major shareholder group's report: one fund bought, another sold; the figures checked are the group's totals.
GROUP = """BÁO CÁO VỀ THAY ĐỔI SỞ HỮU CỦA CỔ ĐÔNG LỚN, NHÀ ĐẦU TƯ NẮM GIỮ TỪ 5% TRỞ LÊN CỔ PHIẾU
5. Số lượng, tỷ lệ cổ phiếu nắm giữ trước khi thực hiện giao dịch/Number, ownership
pDercentage of shares owned before the transaction: 19.508.271 cổ phiếu/shares (1,5666%)
se Quỹ A: 13.500.000 (1,0841%)
6. Số lượng cổ phiếu đã mua/bán (làm tỷ lệ sở hữu có thay đổi qua ngưỡng một phần trăm
(1%)/Number of shares bought/sold: {traded} cổ phiếu/shares
se Quỹ A: mua/purchased 2.500.000
se Quỹ B: mua/purchased 1.280.000
se Quỹ C: bán/sold 398.910
7. Số lượng, tỷ lệ cổ phiếu nắm giữ sau khi thực hiện giao dịch /Number, ownership
percentage of shares owned after the transaction: {after} cổ phiếu/shares (1,8381%)
8. Số lượng, tỷ lệ cổ phiếu người có liên quan đang nắm giữ: 1.000.000
"""


def insider(before="20.623.635", kind="Mua", traded="650.000", after="21.273.635", method="Khớp lệnh"):
    return INSIDER.format(before=before, kind=kind, traded=traded, after=after, method=method)


def test_an_insider_report_counts_only_when_before_plus_traded_is_after():
    assert parse_report(insider(), "Báo cáo kết quả giao dịch cổ phiếu của người nội bộ A") == {
        "kind": "Mua", "shares": 650000, "before": 20623635, "after": 21273635, "rong": False}
    sold = parse_report(insider(kind="Bán", before="21.273.635", after="20.623.635"), "Báo cáo kết quả giao dịch")
    assert (sold["kind"], sold["shares"]) == ("Bán", 650000)
    # One misread digit and the figures no longer add up: nothing is taken
    assert parse_report(insider(after="21.273.685"), "Báo cáo kết quả") == {"reason": "cộng trừ không khớp"}
    # The figures add up the other way round from the kind the report states
    assert parse_report(insider(kind="Bán"), "Báo cáo kết quả") == {"reason": "chiều không khớp"}
    assert parse_report(insider(traded="sáu trăm"), "Báo cáo kết quả") == {"reason": "thiếu số trước, đã giao dịch hoặc sau"}
    assert parse_report("", "Báo cáo kết quả") == {"reason": "thiếu số trước, đã giao dịch hoặc sau"}


ORGANISATION = """1. Tổ chức thực hiện giao dịch: Quỹ X
5. Số lượng, tỷ lệ cổ phiếu nắm giữ trước khi thực hiện giao dịch: 1.638.114 cổ phiều (0,162%)
6. Số lượng cổ phiếu đăng ký Mua: 500.000 cổ phiếu
7. Số lượng cổ phiếu đã {kind}: 141.000 cổ phiếu
8. Giá trị đã giao dịch (tính theo mệnh giá): 1.410.000.000 đồng
9, Số lượng, tỷ lệ cổ phiều nắm giữ sau khi thực hiện giao dịch: {after} cổ phiếu (0,1738%)
"""


def test_an_organisations_report_states_the_kind_in_the_traded_line():
    assert parse_report(ORGANISATION.format(kind="Mua", after="1.779.114"), "Báo cáo kết quả") == {
        "kind": "Mua", "shares": 141000, "before": 1638114, "after": 1779114, "rong": False}
    # A stock dividend received during the trading window: the holding moved by more than the trade, so nothing is taken
    assert parse_report(ORGANISATION.format(kind="Mua", after="1.949.925"), "Báo cáo kết quả") == {"reason": "cộng trừ không khớp"}
    assert parse_report(ORGANISATION.format(kind="Bán", after="1.779.114"), "Báo cáo kết quả") == {"reason": "chiều không khớp"}


def test_an_unreadable_kind_line_leaves_the_direction_to_the_figures():
    text = insider().replace("Loại giao dịch đã thực hiện/73/5e oƒ 1ranSaction executed: Mua/Purchase", "Loai g1ao d|ch: M ua")
    assert parse_report(text, "Báo cáo kết quả")["kind"] == "Mua"


def test_gifts_are_their_own_kinds_and_a_report_of_nothing_traded_says_so():
    given = insider(kind="Cho/tặng", before="18.825.159", traded="17.700.000", after="1.125.159",
                    method="Chuyên quyền sở hữu chứng khoán do cho/tặng qua Tổng Công ty").replace("Cho/tặng/Purchase", "Cho/tặng")
    assert parse_report(given, "Báo cáo kết quả")["kind"] == "Cho tặng"
    got = insider(kind="Được cho/tặng", before="129.383", traded="17.700.000", after="17.829.383").replace("Được cho/tặng/Purchase", "Được cho/tặng")
    assert parse_report(got, "Báo cáo kết quả")["kind"] == "Nhận tặng"
    # the kind line unreadable, the method still says it was a gift
    unread = given.replace("Loại giao dịch đã thực hiện/73/5e oƒ 1ranSaction executed: Cho/tặng", "")
    assert parse_report(unread, "Báo cáo kết quả")["kind"] == "Cho tặng"
    assert parse_report(ORGANISATION.format(kind="Mua", after="1.638.114").replace("141.000", "0"), "Báo cáo kết quả") == {
        "reason": "không giao dịch cổ phiếu nào"}


def test_esop_is_its_own_kind():
    via_title = parse_report(insider(), "Báo cáo kết quả giao dịch cổ phiếu ESOP của Người nội bộ A")
    via_method = parse_report(insider(method="Mua trực tiếp từ tổ chức phát hành/Pzrchase directiy ƒrom the iSsuer"), "Báo cáo kết quả")
    assert via_title["kind"] == via_method["kind"] == "ESOP" and via_title["shares"] == 650000


def test_a_group_report_gives_the_groups_net_change():
    assert parse_report(GROUP.format(traded="3.381.090", after="22.889.361"), "Báo cáo về thay đổi sở hữu của nhóm cổ đông lớn") == {
        "kind": "Mua", "shares": 3381090, "before": 19508271, "after": 22889361, "rong": True}
    down = parse_report(GROUP.format(traded="1.000.000", after="18.508.271"), "Báo cáo về thay đổi sở hữu")
    assert (down["kind"], down["shares"]) == ("Bán", 1000000)
    assert parse_report(GROUP.format(traded="3.381.090", after="22.889.351"), "Báo cáo") == {"reason": "cộng trừ không khớp"}


def test_news_id_only_from_hose_notice_links():
    assert news_id("https://www.hsx.vn/vi/tin-tuc/kdh-bao-cao-ket-qua/2502523") == "2502523"
    assert news_id("https://hnx.vn/vi-vn/tin/1234567") is None
    assert news_id(None) is None


MEDIA = {"data": {"list": [
    {"fileName": "a sign.pdf", "fileType": ".pdf", "filePath": "~/Uploads/UploadDocuments/2502523/a sign.pdf"},
    {"fileName": "b sign.pdf", "fileType": ".pdf", "filePath": "~/Uploads/UploadDocuments/2502523/b sign.pdf"}]}, "success": True}


def _reader(texts, calls):
    def get_json(url):
        calls.append(url)
        return MEDIA

    def get_bytes(url):
        calls.append(url)
        return url.encode()

    def pdf_text(data):
        return [texts[data.decode().rsplit("/", 1)[1]]]
    return get_json, get_bytes, pdf_text


def test_a_notice_with_one_file_per_person_sums_them_and_needs_every_file():
    calls = []
    get_json, get_bytes, pdf_text = _reader({"a%20sign.pdf": insider(), "b%20sign.pdf": insider(before="không rõ", traded="100.000", after="100.000")}, calls)
    rec = read_notice("2502523", "Báo cáo kết quả giao dịch cổ phiếu ESOP", get_json=get_json, get_bytes=get_bytes, pdf_text=pdf_text,
                      sleep=lambda s: None, now=NOW)
    assert calls[0] == "https://api.hsx.vn/m/api/v1/1/mediafiles/1/2502523?pageIndex=1&pageSize=100&year=0"
    assert calls[1] == "https://staticfile.hsx.vn/Uploads/UploadDocuments/2502523/a%20sign.pdf"
    # The second file's "before" is unreadable (the registered 650.000 two lines down is another item); the notice stays without a volume
    assert rec["result"] is None and rec["reason"] == "b sign.pdf: thiếu số trước, đã giao dịch hoặc sau"
    # Holding nothing before (a first ESOP grant) is a plain 0
    get_json, get_bytes, pdf_text = _reader({"a%20sign.pdf": insider(), "b%20sign.pdf": insider(before="0", traded="100.000", after="100.000")}, [])
    rec = read_notice("2502523", "Báo cáo kết quả giao dịch cổ phiếu ESOP", get_json=get_json, get_bytes=get_bytes, pdf_text=pdf_text,
                      sleep=lambda s: None, now=NOW)
    assert rec["result"] == {"kind": "ESOP", "shares": 750000, "files": 2, "rong": False, "before": None, "after": None}
    assert rec["reason"] is None and rec["read_at"] == NOW.isoformat()


def test_a_notice_without_files_or_with_mixed_kinds_is_kept_without_a_volume():
    def none(url):
        return {"data": {"list": []}, "success": True}
    rec = read_notice("1", "Báo cáo", get_json=none, get_bytes=None, pdf_text=None, sleep=lambda s: None, now=NOW)
    assert rec["result"] is None and rec["reason"] == "không có tệp đính kèm"
    get_json, get_bytes, pdf_text = _reader({"a%20sign.pdf": insider(), "b%20sign.pdf": insider(kind="Bán", before="21.273.635", after="20.623.635")}, [])
    rec = read_notice("2502523", "Báo cáo", get_json=get_json, get_bytes=get_bytes, pdf_text=pdf_text, sleep=lambda s: None, now=NOW)
    assert rec["result"] is None and rec["reason"] == "các tệp khác loại"


def test_one_file_keeps_before_and_after():
    get_json, get_bytes, pdf_text = _reader({"a%20sign.pdf": insider()}, [])

    def one(url):
        return {"data": {"list": MEDIA["data"]["list"][:1]}}
    rec = read_notice("2502523", "Báo cáo", get_json=one, get_bytes=get_bytes, pdf_text=pdf_text, sleep=lambda s: None, now=NOW)
    assert rec["result"] == {"kind": "Mua", "shares": 650000, "files": 1, "rong": False, "before": 20623635, "after": 21273635}


def _deal(date, title, doc, kind=None, shares=None):
    return {"date": date, "kind": kind, "shares": shares, "source": "HOSE", "title": title, "url": None, "doc_url": doc}


DOC = "https://www.hsx.vn/vi/tin-tuc/x/{}"


def test_sync_reads_reports_of_watched_tickers_newest_first_once_and_retries_failures(tmp_path):
    store = InsiderStore(tmp_path)
    store.save("KDH", {"symbol": "KDH", "fetched_at": NOW.isoformat(), "deals": [
        _deal("2026-10-01", "Báo cáo kết quả giao dịch cổ phiếu của người nội bộ A", DOC.format(101)),
        _deal("2026-11-01", "Báo cáo về thay đổi sở hữu của nhóm cổ đông lớn", DOC.format(102)),
        _deal("2026-11-02", "Thông báo giao dịch cổ phiếu của người nội bộ A", DOC.format(103)),  # an intention: not read
        _deal("2026-11-03", "Báo cáo kết quả có số VNDirect", DOC.format(104), kind="Mua", shares=5),  # VNDirect has it
        _deal("2026-09-01", "Báo cáo kết quả giao dịch của người nội bộ B", "https://hnx.vn/tin/105"),  # not HOSE
        _deal("2026-08-01", "Báo cáo kết quả cũ", DOC.format(106))]})
    store.save("ACB", {"symbol": "ACB", "fetched_at": NOW.isoformat(), "deals": [_deal("2026-11-20", "Báo cáo kết quả", DOC.format(201))]})
    docs = DocStore(tmp_path)
    docs.save("106", {"news_id": "106", "result": None, "reason": "cộng trừ không khớp"})
    asked = []

    def read(nid, title, **kw):
        asked.append(nid)
        if nid == "101":
            raise OSError("timeout")
        return {"news_id": nid, "title": title, "result": {"kind": "Mua", "shares": 1000, "files": 1, "rong": False,
                                                           "before": 1000, "after": 2000}, "reason": None, "read_at": NOW.isoformat()}
    out = sync_insider_docs(tmp_path, ["KDH"], read=read, limit=30)
    assert asked == ["102", "101"]  # ACB is not watched; 103 is an intention, 104 has VNDirect's figures, 105 is HNX, 106 was read
    assert out == {"read": 1, "accepted": 1, "rejected": 0, "errors": 1, "left": 0}
    assert docs.read("102")["result"]["shares"] == 1000 and docs.read("101") is None  # a failed fetch is tried again next time
    assert sync_insider_docs(tmp_path, ["KDH"], read=read, limit=0) == {"read": 0, "accepted": 0, "rejected": 0, "errors": 0, "left": 1}


def test_readings_fill_only_what_vndirect_lacks_and_esop_is_tallied_apart(tmp_path):
    docs = DocStore(tmp_path)
    docs.save("101", {"news_id": "101", "read_at": NOW.isoformat(), "reason": None,
                      "result": {"kind": "ESOP", "shares": 650000, "files": 4, "rong": False, "before": None, "after": None}})
    docs.save("102", {"news_id": "102", "read_at": NOW.isoformat(), "reason": None,
                      "result": {"kind": "Bán", "shares": 3000, "files": 1, "rong": True, "before": 10000, "after": 7000}})
    docs.save("103", {"news_id": "103", "read_at": NOW.isoformat(), "reason": None,
                      "result": {"kind": "Bán", "shares": 9, "files": 1, "rong": False, "before": 18, "after": 9}})
    docs.save("104", {"news_id": "104", "read_at": NOW.isoformat(), "reason": "cộng trừ không khớp", "result": None})
    deals = [_deal("2026-10-01", "ESOP", DOC.format(101)), _deal("2026-11-01", "Nhóm", DOC.format(102)),
             _deal("2026-11-02", "VNDirect nói mua", DOC.format(103), kind="Mua"), _deal("2026-11-03", "Không khớp", DOC.format(104)),
             _deal("2026-11-04", "Đủ số", DOC.format(102), kind="Mua", shares=7)]
    out = fill_from_docs(deals, docs)
    assert (out[0]["kind"], out[0]["shares"]) == ("ESOP", 650000)
    assert out[0]["tu_van_ban"] == {"truoc": None, "sau": None, "so_tep": 4, "rong": False, "doc_luc": NOW.isoformat()}
    assert (out[1]["kind"], out[1]["shares"], out[1]["tu_van_ban"]["rong"]) == ("Bán", 3000, True)
    assert out[2] == deals[2]  # VNDirect's kind is never overruled
    assert out[3] == deals[3] and out[4] == deals[4]

    store = InsiderStore(tmp_path)
    store.save("KDH", {"symbol": "KDH", "fetched_at": NOW.isoformat(), "deals": deals, "source": "vndirect:finfo"})
    view = insider_deals(store, "KDH", get=None, now=NOW)
    assert view["year"] == {"since": "2025-11-26", "bought": 7, "buy_reports": 1, "sold": 3000, "sell_reports": 1,
                            "esop": 650000, "esop_reports": 1, "gift_reports": 0, "merged_reports": 0, "without_volume": 2}
    assert json.loads((tmp_path / "insider" / "KDH.json").read_text(encoding="utf-8"))["deals"] == deals  # stored as VNDirect gave it


def test_gifts_are_counted_apart_from_buying_and_selling(tmp_path):
    docs = DocStore(tmp_path)
    for nid, kind in (("301", "Cho tặng"), ("302", "Nhận tặng")):
        docs.save(nid, {"news_id": nid, "read_at": "r", "reason": None,
                        "result": {"kind": kind, "shares": 17700000, "files": 1, "rong": False, "before": 1, "after": 2}})
    store = InsiderStore(tmp_path)
    store.save("KDH", {"symbol": "KDH", "fetched_at": NOW.isoformat(), "source": "vndirect:finfo",
                       "deals": [_deal("2026-11-20", "Cho", DOC.format(301)), _deal("2026-11-20", "Nhận", DOC.format(302))]})
    year = insider_deals(store, "KDH", get=None, now=NOW)["year"]
    assert (year["bought"], year["sold"], year["gift_reports"], year["without_volume"]) == (0, 0, 2, 0)


# A foreign investor group's report: a table per member, then the group's total row (before, after, traded).
TABLE = """5. Thông tin chỉ tiết về tình hình giao dịch chứng khoán của các thành viên trong nhóm
2| Longwoods
gw cu 22.000.000 | 1,7666 | 23.000.000. | 1,8469 | 1.000.000
Tổng cả nhóm nhà đầu tư nước ngoài có liên quan/Total
. „ ố . S {before} | 7,9739 | {after} | 8,0542 | {traded}
group of affiliated foreign Investors
6. Ngày thay đổi tỷ lệ sở hữu của cả nhóm
"""


def test_a_foreign_groups_table_is_read_from_its_total_row():
    assert parse_report(TABLE.format(before="99.298.874", after="100.298.874", traded="1.000.000"), "Báo cáo về sở hữu của nhóm NĐTNN") == {
        "kind": "Mua", "shares": 1000000, "before": 99298874, "after": 100298874, "rong": True}
    # a decrease is printed in brackets; the total on the same line as its label, percentages with a dot
    one_line = "Tổng cả nhóm đầu tư nước ngoài có liên quan/ 62.902.841 5,0512% | 62.192.841 4.9942% (710.000)\nTotal group\n"
    assert parse_report(one_line, "Báo cáo")["kind"] == "Bán" and parse_report(one_line, "Báo cáo")["shares"] == 710000
    assert parse_report(TABLE.format(before="99.298.874", after="100.298.874", traded="1.000.001"), "Báo cáo") == {"reason": "cộng trừ không khớp"}
    # an empty total row
    assert parse_report("Tổng cả nhóm đâu tư nước ngoài có liên quan/\nTotal group oƒ affliated foreign investors\nGhi chú/Notes:\n", "Báo cáo") == {
        "reason": "thiếu số trước, đã giao dịch hoặc sau"}
