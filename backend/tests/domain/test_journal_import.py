from datetime import date

import pytest

from investment_agent.domain.journal_import import ImportFileError, parse_journal_file

TODAY = date(2026, 11, 8)
HEAD = "STT,Loại tài sản,Ngày giao dịch,Lệnh,Mã,SL tổng,Giá vốn,Giá trị vốn,Lãi/Lỗ,Lý do mua/ bán\n"


def _xml(*rows):
    cells = "".join("<Row>" + "".join(c for c in row) + "</Row>\n" for row in rows)
    return ('<?xml version="1.0"?>\n<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
            'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="NhatKy"><Table>\n' + cells + "</Table></Worksheet></Workbook>")


def s(v):
    return f'<Cell><Data ss:Type="String">{v}</Data></Cell>'


def n(v):
    return f'<Cell><Data ss:Type="Number">{v}</Data></Cell>'


HEADER = [s(h) for h in ("STT", "Loại tài sản", "Ngày giao dịch", "Lệnh", "Mã", "SL tổng", "Giá vốn", "Giá trị vốn", "Lãi/Lỗ", "Lý do mua/ bán")]


def test_the_old_journals_excel_export_is_read_with_its_totals_row_left_out():
    text = _xml(HEADER,
                [n(1), s("Cổ phiếu"), s("2025-03-01"), s("Mua"), s("HPG"), n(1000), n(20000.5), n(20000500), n(0), s("Định giá rẻ &amp; hỗ trợ")],
                [n(2), s("Cổ phiếu"), s("2025-04-01"), s("Bán"), s("HPG"), n(1000), n(25000), n(25000000), n(-500000), s("Chốt")],
                ['<Cell ss:Index="1" ss:MergeAcross="6"><Data ss:Type="String">Tổng cộng:</Data></Cell>',
                 '<Cell ss:Index="8"><Data ss:Type="Number">45000500</Data></Cell>', '<Cell ss:Index="9"><Data ss:Type="Number">-500000</Data></Cell>'])
    entries, problems = parse_journal_file(text, today=TODAY)
    assert problems == [] and len(entries) == 2
    buy, sell = entries
    assert buy.symbol == "HPG" and buy.kind == "buy" and buy.created_on == date(2025, 3, 1) and buy.reason == "Định giá rẻ & hỗ trợ"
    assert buy.imported == {"asset": "Cổ phiếu", "ticker": "HPG", "qty": "1000", "price": "20000.5", "total": "20000500", "pnl": None}  # a buy has no P&L
    assert buy.context == {} and sell.kind == "sell" and sell.imported["pnl"] == "-500000"


def test_csv_with_vietnamese_numbers_and_either_separator_is_read_and_a_missing_total_is_price_times_quantity():
    entries, problems = parse_journal_file("﻿" + HEAD + '1,Cổ phiếu,01/03/2025,Mua,fpt,"1.000","20.000,5",,,"Rẻ, tốt"\n', today=TODAY)
    assert problems == [] and entries[0].symbol == "FPT" and entries[0].created_on == date(2025, 3, 1) and entries[0].reason == "Rẻ, tốt"
    assert entries[0].imported["qty"] == "1000" and entries[0].imported["price"] == "20000.5" and entries[0].imported["total"] == "20000500"
    entries, _ = parse_journal_file(HEAD.replace(",", ";") + "1;Cổ phiếu;2025-03-01;Bán;FPT;100;50000;5000000;1.500.000;x\n", today=TODAY)
    assert entries[0].imported["pnl"] == "1500000"


def test_a_bad_line_is_reported_with_its_number_and_never_guessed():
    text = (HEAD + "1,Cổ phiếu,31/02/2025,Mua,HPG,1,1,,,a\n"  # no such date: the old page silently wrote today
            "2,Cổ phiếu,2027-01-01,Mua,HPG,1,1,,,b\n"  # after today
            "3,Cổ phiếu,2025-03-01,Giữ lâu dài?,HPG,1,1,,,c\n"
            "4,Cổ phiếu,2025-03-01,Mua,HPG,abc,1,,,d\n"
            "5,Cổ phiếu,2025-03-01,Mua,HOA PHAT,1,1,,,e\n"
            "6,Cổ phiếu,2025-03-01,Mua,HPG,,,,,f\n"
            "7,Cổ phiếu,2025-03-02,Mua,HPG,2,3,,,ok\n")
    entries, problems = parse_journal_file(text, today=TODAY)
    assert [e.reason for e in entries] == ["ok"]
    assert [p["line"] for p in problems] == [2, 3, 4, 5, 6, 7]
    assert "31/02/2025" in problems[0]["message"] and "HOA PHAT" in problems[4]["message"]


def test_other_assets_are_kept_under_a_stand_in_code_with_their_own_name():
    entries, problems = parse_journal_file(HEAD + "1,Bất động sản,2025-03-01,Mua,Đất Long An,,,1500000000,,Mua đất\n2,Vàng,2025-03-02,Mua,,2,8000000,,,x\n3,Bitcoin,2025-03-03,Mua,BTC,1,1,,,y\n",
                                           today=TODAY)
    assert problems == [] and [e.symbol for e in entries] == ["BDS", "VANG", "BTC"]
    assert entries[0].imported["ticker"] == "Đất Long An" and entries[0].imported["asset"] == "Bất động sản"


def test_identical_lines_are_both_kept_and_each_line_has_the_same_id_on_every_import():
    text = HEAD + "1,Cổ phiếu,2025-03-01,Mua,HPG,1,1,,,a\n2,Cổ phiếu,2025-03-01,Mua,HPG,1,1,,,a\n"
    first, _ = parse_journal_file(text, today=TODAY)
    second, _ = parse_journal_file(text, today=TODAY)
    assert len({e.entry_id for e in first}) == 2 and [e.entry_id for e in first] == [e.entry_id for e in second]


def test_a_file_without_the_needed_columns_or_with_entity_declarations_is_refused():
    with pytest.raises(ImportFileError, match="cột"):
        parse_journal_file("a,b\n1,2\n", today=TODAY)
    with pytest.raises(ImportFileError):
        parse_journal_file('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><Workbook/>', today=TODAY)
    with pytest.raises(ImportFileError):
        parse_journal_file("", today=TODAY)
