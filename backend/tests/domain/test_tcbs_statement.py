import io
import zipfile
from datetime import date

import pytest

from investment_agent.domain.tcbs_statement import StatementFileError, parse_tcbs_xlsx

TODAY = date(2026, 11, 9)
HEADER = ["Mã CP\nTicker", "Ngày GD\nTrading date", "Giao dịch\nTrade", "KL đặt\nVolume", "Giá đặt (VND)\nOrder price", "KL khớp\nMatched volume", "Giá khớp (VND)\nMatched price",
          "Giá trị khớp (VND)\nMatched value", "Phí (VND)\nFee (vnd)", "Thuế (VND)\nTax (VND)", "Giá vốn\nCost", "Lãi lỗ (VND)\nReturn", "Kênh GD\nChannel", "Trạng thái\nStatus",
          "Loại lệnh\nOrder type", "Số hiệu lệnh\nOrder No."]


def line(ticker="AAA", day="05/10/2026", side="Mua", qty=100, price=20000, fee=300, tax=0, status="Hoàn tất", order="111"):
    return [ticker, day, side, qty, price, qty, price, qty * price, fee, tax, price, 0, "Online", status, "Lệnh thường", order]


def xlsx(rows):
    """A minimal workbook laid out as TCInvest exports it: a letterhead, then the table, then a footnote."""
    def cell(ref, v):
        if isinstance(v, str):
            text = v.replace("&", "&amp;").replace("<", "&lt;")
            return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'
        return f'<c r="{ref}"><v>{v}</v></c>'
    out = []
    for r, row in enumerate(rows, start=1):
        out.append(f'<row r="{r}">' + "".join(cell(f"{chr(65 + c)}{r}", v) for c, v in enumerate(row) if v is not None) + "</row>")
    sheet = '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + "".join(out) + "</sheetData></worksheet>"
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return b.getvalue()


def book(*lines):
    return xlsx([["Tên công ty"], ["Khách hàng", "ẩn danh"], ["Mã CP (Ticker)", "Tất cả"], ["Giao dịch (Trade)", "Tất cả"], HEADER, *lines, ["Tổng"], ["Chú thích: báo cáo tự động."]])


def test_matched_orders_are_read_with_their_fees_and_order_numbers_and_the_letterhead_and_footnote_left_out():
    rows, problems = parse_tcbs_xlsx(book(line(), line("BBB", "06/10/2026", "Bán", 50, 30000, 200, 1500, order="222")), today=TODAY)
    assert problems == [] and len(rows) == 2
    assert rows[0] == {"line": 6, "symbol": "AAA", "type": "buy", "date": date(2026, 10, 5), "quantity": 100, "price": "20000", "fee": "300", "tax": "0", "order_no": "111"}
    assert rows[1]["type"] == "sell" and rows[1]["tax"] == "1500"


def test_a_bad_line_is_reported_by_number_and_left_out():
    bad = [line(day="31/02/2026", order="1"), line(day="10/12/2026", order="2"), line(side="Khác", order="3"), line(status="Đã hủy", order="4"), line(order=""),
           [*line(order="6")[:8], None, *line(order="6")[9:]], line(qty=0, order="7"), line(order="8")]
    rows, problems = parse_tcbs_xlsx(book(*bad), today=TODAY)
    assert [r["order_no"] for r in rows] == ["8"] and [p["line"] for p in problems] == [6, 7, 8, 9, 10, 11, 12]
    assert "31/02/2026" in problems[0]["message"] and "Phí" in problems[5]["message"]


def test_a_file_that_is_not_a_tcbs_statement_is_refused():
    with pytest.raises(StatementFileError):
        parse_tcbs_xlsx(b"not a zip", today=TODAY)
    with pytest.raises(StatementFileError, match="cột"):
        parse_tcbs_xlsx(xlsx([["a", "b"], [1, 2]]), today=TODAY)
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><worksheet/>')
    with pytest.raises(StatementFileError):
        parse_tcbs_xlsx(b.getvalue(), today=TODAY)
