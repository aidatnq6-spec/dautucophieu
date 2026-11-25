import json
from decimal import Decimal

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings, OwnerContext
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.deposit_book import RECORD as BOOK

from signed_client import SECRET, TOKEN, Clock, call

PAGES = ["Báo cáo tài chính hợp nhất. Đơn vị tính: triệu đồng.", "Thuyết minh 5. Phải thu khách hàng 8.595.123.",
         "Thuyết minh 38. Giao dịch với các bên liên quan. Phải thu bên liên quan khác 2.953.000, không được đảm bảo, không hưởng lãi."]


class Done:
    def __init__(self, content):
        self.content, self.cost_usd = content, Decimal("0.01")


class FakeGateway:
    def __init__(self, *answers):
        self.answers, self.sent = list(answers), []

    def complete(self, task, messages, *, job_id, response_format=None):
        self.sent.append((task, messages))
        return Done(self.answers.pop(0))


def client(tmp_path, gateway):
    (tmp_path / "market-symbols.txt").write_text("VJC\nHPG\n", encoding="utf-8")
    clock = Clock()
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(OwnerContext(uid="owner-1", role="owner", correlation_id="t"), *BOOK, {"accounts": [{"id": "a", "name": "Quỹ hưu", "amount": "1000000", "liquid": True}], "deposits": []},
               expected_version=0, request_id="seed-book")
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=repo, data_dir=tmp_path)
    app.state.ai_gateway = gateway
    app.state.ai_document = lambda url: PAGES  # the download and text extraction, faked
    app.state.ai_resolve = lambda host: ["93.184.216.34"]  # a public address, without asking the network
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock


URL = "https://example.vn/vjc-bctc-2020.pdf"


def test_a_question_about_a_public_document_is_answered_with_its_pages(tmp_path):
    gw = FakeGateway(json.dumps({"answer": "Phải thu bên liên quan khác 2.953.000 triệu đồng, không đảm bảo, không lãi.", "pages": [3]}))
    c, clock = client(tmp_path, gw)
    body = call(c, clock, "POST", "/internal/ai-docs/VJC/ask", {"url": URL, "question": "Thuyết minh 38 nói gì về phải thu bên liên quan?"}).json()
    assert body["status"] == "ok" and body["pages"] == [3] and "2.953.000" in body["answer"] and body["url"] == URL
    task, messages = gw.sent[0]
    sent = json.dumps(messages, ensure_ascii=False)
    assert task == "doc_qa" and json.loads(messages[1]["content"])["ticker"] == "VJC"
    assert "Quỹ hưu" not in sent and "HPG" not in sent and "1000000" not in sent  # nothing of the owner's goes out


def test_a_question_naming_the_owners_own_row_or_an_amount_is_never_sent(tmp_path):
    gw = FakeGateway()
    c, clock = client(tmp_path, gw)
    for q, reason in (("Quỹ hưu có nên mua VJC?", "personal_name"), ("Phải thu 2.953 tỷ có thật không?", "amount"), ("So với HPG thì sao?", "other_ticker")):
        r = call(c, clock, "POST", "/internal/ai-docs/VJC/ask", {"url": URL, "question": q})
        assert r.status_code == 422 and r.json()["code"] == f"blocked_{reason}"
    assert gw.sent == []


def test_an_answer_quoting_a_number_not_in_the_document_gets_one_repair_then_is_withheld(tmp_path):
    bad = json.dumps({"answer": "Khoảng 4.100.000 triệu đồng.", "pages": [3]})
    gw = FakeGateway(bad, bad)
    c, clock = client(tmp_path, gw)
    body = call(c, clock, "POST", "/internal/ai-docs/VJC/ask", {"url": URL, "question": "Phải thu bên liên quan là bao nhiêu?"}).json()
    assert body["status"] == "unverified" and body["answer"] is None and len(gw.sent) == 2


def test_rows_for_the_related_receivables_book_are_proposed_never_saved(tmp_path):
    gw = FakeGateway(json.dumps({"unit": "triệu đồng", "rows": [
        {"name": "Bên liên quan khác", "amount_text": "2.953.000", "page": 3, "related": True, "grouped": True, "secured": False, "interest": False,
         "collect_within": None},
        {"name": "Công ty Bịa", "amount_text": "9.999.999", "page": 3, "related": True, "grouped": False, "secured": None, "interest": None,
         "collect_within": None}]}))
    c, clock = client(tmp_path, gw)
    body = call(c, clock, "POST", "/internal/ai-docs/VJC/related-receivables", {"url": URL, "year": "2020"}).json()
    assert body["status"] == "ok" and [r["name"] for r in body["rows"]] == ["Bên liên quan khác"] and body["rows"][0]["amount"] == "2953"
    assert body["dropped"] == [{"name": "Công ty Bịa", "reason": "amount_not_on_page"}] and gw.sent[0][0] == "notes_extract"
    assert call(c, clock, "GET", "/internal/related-receivables/VJC").json()["years"] == []  # nothing saved by the AI


def test_unsafe_links_and_unwatched_tickers_are_refused(tmp_path):
    c, clock = client(tmp_path, FakeGateway())
    assert call(c, clock, "POST", "/internal/ai-docs/VJC/ask", {"url": "http://example.vn/a.pdf", "question": "Có gì?"}).json()["code"] == "unsafe_url"
    assert call(c, clock, "POST", "/internal/ai-docs/FPT/ask", {"url": URL, "question": "Có gì?"}).status_code == 404


def test_a_draft_for_the_notes_block_is_proposed_with_its_pages_never_saved_owner_25_11_2026(tmp_path):
    """AI soạn nháp Thuyết minh TSCĐ: one notes_extract call; only the ticker, the year and passages go out; nothing is saved."""
    gw = FakeGateway(json.dumps({"unit": "triệu đồng", "projects": [], "ranges": [], "prepaid": [], "deals": [], "capitalised_interest": None,
                                 "incentives": [], "extra": "ignored"}))
    c, clock = client(tmp_path, gw)
    body = call(c, clock, "POST", "/internal/ai-docs/HPG/notes-draft", {"url": URL, "year": "2021"}).json()
    assert body["status"] == "ok" and body["draft"]["projects"] == [] and body["cost_usd"] == "0.01" and "spend" in body
    task, messages = gw.sent[0]
    assert task == "notes_extract" and set(json.loads(messages[1]["content"])) == {"ticker", "year", "passages"}
    assert "Quỹ hưu" not in json.dumps(messages, ensure_ascii=False)  # the owner's own rows never go out
    bad = call(c, clock, "POST", "/internal/ai-docs/HPG/notes-draft", {"url": URL, "year": "21"})
    assert bad.status_code == 422
