"""AI soạn nháp Thuyết minh TSCĐ (spec 2026-11-25-ai-soan-nhap-thuyet-minh-design.md): only the ticker, the year and passages go out; every
figure the model gives must stand verbatim on the page it names, or the line is dropped with why; nothing is saved."""

import json

import pytest

from investment_agent.ai.doc_ask import Unverified
from investment_agent.ai.notes_draft import check_notes, notes_messages, notes_passages

PAGES = ["Báo cáo tài chính hợp nhất năm 2021. Đơn vị tính: tỷ đồng.",
         "13. Chi phí xây dựng cơ bản dở dang. Dự án Khu liên hợp Gang thép Dung Quất 2: 8.289,3, dự kiến hoàn thành quý 4 năm 2024.",
         "3.7 Tài sản cố định hữu hình. Thời gian khấu hao: nhà cửa, vật kiến trúc 5 - 50 năm; máy móc, thiết bị 1 - 25 năm.",
         "17. Chi phí trả trước. Phân bổ công cụ dụng cụ 109; phân bổ chi phí sửa chữa lớn 139. Chi phí đi vay được vốn hóa trong năm 412.",
         "3.1 Hợp nhất kinh doanh. Ngày 29/03/2021 mua 69,87% Công ty Cổ phần Greenland, giá mua 2.859,9; giá trị hợp lý tài sản thuần 3.896,1; "
         "lợi thế thương mại 103.",
         "40.3 Thuế TNDN. Công ty Thép Dung Quất được áp dụng thuế suất 10% đến hết năm 2026."]


def answer(**more):
    base = {"unit": "tỷ đồng",
            "projects": [{"name": "Khu liên hợp Gang thép Dung Quất 2", "cip_text": "8.289,3", "due_text": "quý 4 năm 2024", "page": 2},
                         {"name": "Dự án bịa", "cip_text": "1.234", "due_text": None, "page": 2}],
            "ranges": [{"group": "buildings", "from": 5, "to": 50, "page": 3}, {"group": "machinery", "from": 1, "to": 25, "page": 3},
                       {"group": "vehicles", "from": 1, "to": 30, "page": 3}],
            "prepaid": [{"kind": "tools", "amount_text": "109", "page": 4}, {"kind": "overhaul", "amount_text": "139", "page": 4}],
            "deals": [{"name": "Công ty Cổ phần Greenland", "date_text": "29/03/2021", "share_text": "69,87", "price_text": "2.859,9",
                       "net_assets_text": "3.896,1", "goodwill_text": "103", "page": 5}],
            "capitalised_interest": {"amount_text": "412", "page": 4},
            "incentives": [{"entity": "Công ty Thép Dung Quất", "kind": "rate", "rate_text": "10", "until_text": "2026", "page": 6}]}
    base.update(more)
    return json.dumps(base)


def test_only_the_ticker_the_year_and_passages_go_out():
    passages = notes_passages(PAGES)
    assert {n for n, _ in passages} >= {2, 3, 4, 5, 6}
    messages = notes_messages("HPG", "2021", passages)
    sent = json.loads(messages[1]["content"])
    assert set(sent) == {"ticker", "year", "passages"} and sent["ticker"] == "HPG" and sent["year"] == "2021"


def test_each_figure_stands_on_its_page_or_the_line_is_dropped():
    draft, dropped = check_notes(answer(), notes_passages(PAGES), document_text=" ".join(PAGES))
    assert draft["projects"] == [{"name": "Khu liên hợp Gang thép Dung Quất 2", "cip_value": "8289.3", "due": "Q4/2024", "due_text": "quý 4 năm 2024", "page": 2}]
    assert draft["ranges"] == {"buildings": {"from": 5, "to": 50, "page": 3}, "machinery": {"from": 1, "to": 25, "page": 3}}
    assert draft["prepaid"] == {"tools": {"amount": "109", "page": 4}, "overhaul": {"amount": "139", "page": 4}}
    assert draft["deals"] == [{"name": "Công ty Cổ phần Greenland", "date": "29/03/2021", "share": "69.87", "price": "2859.9", "net_assets": "3896.1",
                               "note_goodwill": "103", "page": 5}]
    assert draft["capitalised_interest"] == {"amount": "412", "page": 4}
    assert draft["incentives"] == [{"entity": "Công ty Thép Dung Quất", "kind": "rate", "rate": "10", "until": "2026", "page": 6}]
    assert {(d["part"], d["name"], d["reason"]) for d in dropped} == {("projects", "Dự án bịa", "number_not_on_page"),
                                                                      ("ranges", "vehicles", "number_not_on_page")}


def test_a_year_alone_leaves_the_quarter_blank_and_a_wrong_page_or_unit_is_refused():
    draft, _ = check_notes(answer(projects=[{"name": "Khu liên hợp Gang thép Dung Quất 2", "cip_text": "8.289,3", "due_text": "năm 2024", "page": 2}]),
                           notes_passages(PAGES), document_text=" ".join(PAGES))
    assert draft["projects"][0]["due"] == ""
    _, dropped = check_notes(answer(capitalised_interest={"amount_text": "412", "page": 9}), notes_passages(PAGES), document_text=" ".join(PAGES))
    assert {"part": "capitalised_interest", "name": "", "reason": "page_not_sent"} in dropped
    with pytest.raises(Unverified):
        check_notes(answer(unit="nghìn tỷ"), notes_passages(PAGES), document_text=" ".join(PAGES))
    with pytest.raises(Unverified):
        check_notes("not json", notes_passages(PAGES), document_text=" ".join(PAGES))
