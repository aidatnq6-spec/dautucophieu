from datetime import date, datetime, timezone

from investment_agent.api.auth import OwnerContext
from investment_agent.domain.property_book import PropertyBook
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.attention import attention_items
from investment_agent.services.insurance_alerts import due_lines, insurance_alerts_run
from investment_agent.services.property_book import RECORD

TODAY = date(2027, 4, 10)
HOUSE = {"id": "h", "name": "Bảo hiểm nhà", "kind": "property", "premium": "3000000", "frequency": "year", "due_on": "2026-05-05"}


def book(*policies):
    return PropertyBook.model_validate({"policies": list(policies)})


def test_a_premium_is_named_from_thirty_days_before_it_is_due():
    assert due_lines(book(HOUSE), TODAY) == ["Bảo hiểm nhà: đóng phí 3.000.000 đ ngày 05/05/2027, còn 25 ngày"]
    assert due_lines(book(HOUSE), date(2027, 4, 4)) == []  # 31 days before
    assert due_lines(book(HOUSE), date(2027, 5, 5)) == ["Bảo hiểm nhà: đóng phí 3.000.000 đ hôm nay (05/05/2027)"]
    assert due_lines(book({**HOUSE, "premium": None}), TODAY) == ["Bảo hiểm nhà: đóng phí ngày 05/05/2027, còn 25 ngày (chưa nhập số phí)"]
    assert due_lines(None, TODAY) == []


def test_telegram_once_per_policy_and_due_date_and_again_next_year(tmp_path):
    sent = []
    keep = lambda t: sent.append(t) or True  # noqa: E731
    assert insurance_alerts_run(tmp_path, book=book(HOUSE), today=TODAY, send=lambda t: False) == {"alerts": 1, "sent": False}
    assert insurance_alerts_run(tmp_path, book=book(HOUSE), today=TODAY, send=keep) == {"alerts": 1, "sent": True}
    assert insurance_alerts_run(tmp_path, book=book(HOUSE), today=date(2027, 4, 20), send=keep) == {"alerts": 0, "sent": False}
    assert insurance_alerts_run(tmp_path, book=book(HOUSE), today=date(2028, 4, 10), send=keep) == {"alerts": 1, "sent": True}
    assert len(sent) == 2 and "Bảo hiểm nhà" in sent[0] and "khuyến nghị" in sent[0]


def test_a_premium_due_is_in_vic_can_xem(tmp_path):
    owner = OwnerContext("owner-1", "owner", "test")
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(owner, *RECORD, book(HOUSE).model_dump(mode="json"), expected_version=0, request_id="pb1")
    items = attention_items(repo, owner, tmp_path, now=datetime(2027, 4, 10, 3, tzinfo=timezone.utc))
    assert {"level": "high", "kind": "insurance_due", "symbol": None, "text": "Bảo hiểm nhà: đóng phí 3.000.000 đ ngày 05/05/2027, còn 25 ngày", "href": "/profile?tab=tai-san"} in items
