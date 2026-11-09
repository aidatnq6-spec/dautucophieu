import json
from datetime import date, datetime, timezone

from investment_agent.api.auth import OwnerContext
from investment_agent.domain.property_book import PropertyBook
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.attention import attention_items
from investment_agent.services.loan_alerts import loan_alerts_run, promo_lines
from investment_agent.services.property_book import RECORD

TODAY = date(2026, 11, 9)
LOAN = {"id": "l", "name": "Vay nhà", "balance": "1200000000", "rate": "8", "promo_ends": "2027-01-01", "after_rate": "12", "months_left": 120, "method": "declining"}


def book(*loans):
    return PropertyBook.model_validate({"loans": list(loans)})


def run(tmp_path, b, today=TODAY, ok=True):
    texts = []
    out = loan_alerts_run(tmp_path, book=b, today=today, send=lambda t: texts.append(t) or ok)
    return out, texts


def test_the_line_gives_the_days_left_and_the_payment_before_and_after():
    assert promo_lines(book(LOAN), TODAY) == ["Vay nhà: hết ưu đãi sau 53 ngày (01/01/2027), khoản trả 18.000.000 đ lên 22.000.000 đ"]  # 10 tr gốc + 8 tr lãi, then + 12 tr lãi


def test_the_window_is_ninety_days_and_the_ending_day_itself():
    assert len(promo_lines(book({**LOAN, "promo_ends": "2027-02-07"}), TODAY)) == 1  # 90 days away
    assert promo_lines(book({**LOAN, "promo_ends": "2027-02-08"}), TODAY) == []
    assert promo_lines(book({**LOAN, "promo_ends": "2026-11-09"}), TODAY) == ["Vay nhà: hết ưu đãi hôm nay (09/11/2026), khoản trả 18.000.000 đ lên 22.000.000 đ"]
    assert promo_lines(book({**LOAN, "promo_ends": "2026-11-08"}), TODAY) == []
    assert promo_lines(book({**LOAN, "promo_ends": None}), TODAY) == []


def test_a_figure_not_entered_is_said_and_no_payment_is_made_up():
    assert promo_lines(book({**LOAN, "after_rate": None}), TODAY) == ["Vay nhà: hết ưu đãi sau 53 ngày (01/01/2027), chưa nhập đủ số để tính khoản trả sau ưu đãi"]
    assert promo_lines(book({**LOAN, "balance": None}), TODAY) == ["Vay nhà: hết ưu đãi sau 53 ngày (01/01/2027), chưa nhập đủ số để tính khoản trả sau ưu đãi"]


def test_the_soonest_comes_first():
    later = {**LOAN, "id": "m", "name": "Vay B", "promo_ends": "2027-01-20"}
    sooner = {**LOAN, "id": "n", "name": "Vay A", "promo_ends": "2026-12-01"}
    assert [x.split(":")[0] for x in promo_lines(book(later, sooner), TODAY)] == ["Vay A", "Vay B"]


def test_a_loan_is_reminded_once_and_the_state_holds_no_amounts(tmp_path):
    out, texts = run(tmp_path, book(LOAN))
    assert out == {"alerts": 1, "sent": True}
    assert texts[0].startswith("Sắp hết lãi ưu đãi\n• Vay nhà: hết ưu đãi sau 53 ngày") and "Không phải khuyến nghị" in texts[0] and "dư nợ hiện tại" in texts[0]
    assert run(tmp_path, book(LOAN), today=date(2026, 11, 10)) == ({"alerts": 0, "sent": False}, [])
    assert json.loads((tmp_path / "alerts" / "loans.json").read_text(encoding="utf-8")) == {"l": "2027-01-01"}


def test_a_failed_send_is_retried_a_new_date_is_reminded_and_no_book_does_nothing(tmp_path):
    assert run(tmp_path, book(LOAN), ok=False)[0] == {"alerts": 1, "sent": False}
    assert run(tmp_path, book(LOAN))[0] == {"alerts": 1, "sent": True}
    assert run(tmp_path, book({**LOAN, "promo_ends": "2027-01-15"}))[0] == {"alerts": 1, "sent": True}
    assert run(tmp_path, None)[0] == {"alerts": 0, "sent": False}


def test_it_is_among_the_things_to_look_at(tmp_path):
    owner = OwnerContext("owner-1", "owner", "test")
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    data = tmp_path / "data"
    data.mkdir()
    (data / "market-symbols.txt").write_text("KDH\n", encoding="utf-8")
    repo.write(owner, *RECORD, book(LOAN).model_dump(mode="json"), expected_version=0, request_id="p1")
    items = [i for i in attention_items(repo, owner, data, now=datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)) if i["kind"] == "loan_promo"]
    assert items == [{"level": "high", "kind": "loan_promo", "symbol": None, "text": "Vay nhà: hết ưu đãi sau 53 ngày (01/01/2027), khoản trả 18.000.000 đ lên 22.000.000 đ", "href": "/profile?tab=tai-san"}]
