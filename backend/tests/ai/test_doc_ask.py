import json

import pytest

from investment_agent.ai.doc_ask import (
    Blocked, Unverified, check_answer, check_rows, qa_messages, rr_messages, screen_question, select_passages,
)

NAMES = {"Quỹ hưu", "TK cho con"}  # the owner's own row names, matched here only
TICKERS = {"FPT", "HPG", "VJC", "VCB"}


@pytest.mark.parametrize("question, reason", [
    ("Công ty có khoản phải thu 2.820 tỷ không?", "amount"),
    ("Doanh thu 15000 có đúng không", "amount"),
    ("Tôi đang nắm mã này, rủi ro gì?", "personal"),
    ("Danh mục của tôi có nên giữ?", "personal"),
    ("Giá vốn hợp lý là bao nhiêu", "personal"),
    ("Quỹ hưu có nên mua mã này", "personal_name"),
    ("So với HPG thì sao?", "other_ticker"),
    ("x" * 301, "too_long"),
    ("  ", "empty"),
])
def test_a_question_carrying_amounts_the_owner_or_another_ticker_is_blocked(question, reason):
    with pytest.raises(Blocked) as exc:
        screen_question(question, symbol="VJC", personal_names=NAMES, tickers=TICKERS)
    assert exc.value.reason == reason


@pytest.mark.parametrize("question", [
    "Thuyết minh 38 năm 2020 nói gì về phải thu bên liên quan?",
    "BCTC quý 3/2026 giải thích biên gộp giảm thế nào?",
    "VJC có khoản phải thu nào không được đảm bảo?",
])
def test_plain_questions_about_the_document_pass(question):
    assert screen_question(question, symbol="VJC", personal_names=NAMES, tickers=TICKERS) == question.strip()


PAGES = ["Bảng cân đối kế toán. Tiền 100.", "Thuyết minh 5. Phải thu khách hàng 8.595.123 triệu đồng.",
         "Thuyết minh 38. Giao dịch với các bên liên quan. Phải thu bên liên quan khác 2.953.000 triệu đồng, không được đảm bảo, không hưởng lãi.",
         "Ý kiến kiểm toán."]


def test_passages_are_the_pages_most_about_the_question_in_page_order_within_the_cap():
    picked = select_passages(PAGES, "phải thu bên liên quan", max_words=60)
    assert [p for p, _ in picked] == [2, 3]  # 1-based pages, the most relevant first chosen, then set back in page order
    assert select_passages([""] * 3, "phải thu", max_words=100) == []


def test_the_messages_carry_the_ticker_the_question_and_the_passages_and_nothing_else():
    passages = select_passages(PAGES, "phải thu bên liên quan", max_words=200)
    msgs = qa_messages("VJC", "Phải thu bên liên quan gồm gì?", passages)
    sent = json.dumps(msgs, ensure_ascii=False)
    assert msgs[0]["role"] == "system" and "chỉ dựa trên các đoạn" in msgs[0]["content"]
    body = json.loads(msgs[1]["content"])
    assert set(body) == {"ticker", "question", "passages"} and body["ticker"] == "VJC"
    assert [p["page"] for p in body["passages"]] == [2, 3] and "Quỹ hưu" not in sent
    rr = json.loads(rr_messages("VJC", "2020", passages)[1]["content"])
    assert set(rr) == {"ticker", "year", "passages"}


def test_an_answer_must_cite_pages_it_was_given_and_quote_only_numbers_in_them():
    passages = select_passages(PAGES, "phải thu bên liên quan", max_words=200)
    ok = check_answer(json.dumps({"answer": "Phải thu bên liên quan khác 2.953.000 triệu đồng, không đảm bảo (trang 3).", "pages": [3]}), passages)
    assert ok == {"answer": "Phải thu bên liên quan khác 2.953.000 triệu đồng, không đảm bảo (trang 3).", "pages": [3]}
    for bad in ('{"answer": "Phải thu 4.100.000 triệu đồng.", "pages": [3]}',  # a number not in the passages
                '{"answer": "Có.", "pages": [9]}',                               # a page not sent
                '{"answer": "Có.", "pages": []}', "không phải JSON"):
        with pytest.raises(Unverified):
            check_answer(bad, passages)


def test_proposed_rows_keep_only_amounts_found_on_their_page_converted_to_ty():
    passages = select_passages(PAGES, "phải thu bên liên quan", max_words=200)
    out = json.dumps({"unit": "triệu đồng", "rows": [
        {"name": "Bên liên quan khác", "amount_text": "2.953.000", "page": 3, "related": True, "grouped": True, "secured": False,
         "interest": False, "collect_within": None},
        {"name": "Công ty Bịa", "amount_text": "1.234.000", "page": 3, "related": True, "grouped": False, "secured": None, "interest": None,
         "collect_within": None}]})
    rows, dropped = check_rows(out, passages, document_text=" ".join(PAGES))
    assert rows == [{"name": "Bên liên quan khác", "amount": "2953", "grouped": True, "related": True, "secured": False, "interest": False,
                     "collect_within": None, "page": 3}]
    assert dropped == [{"name": "Công ty Bịa", "reason": "amount_not_on_page"}]
    with pytest.raises(Unverified):  # a unit the document never states
        check_rows(json.dumps({"unit": "tỷ đồng", "rows": []}), passages, document_text=" ".join(PAGES))
