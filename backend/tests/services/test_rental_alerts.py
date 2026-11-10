from datetime import date, datetime, timezone

from investment_agent.api.auth import OwnerContext
from investment_agent.domain.rental_book import RentalBook
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.attention import attention_items
from investment_agent.services.rental_alerts import RECORD, rental_alerts_run

U = {"id": "u1", "name": "301", "tenant": "Khách A", "rent": "7000000", "due_day": 8, "start": "2026-11-01"}


def book():
    return RentalBook.model_validate({"units": [U], "payments": []})


def test_telegram_once_per_room_and_month_and_again_next_month(tmp_path):
    sent = []
    keep = lambda t: sent.append(t) or True  # noqa: E731
    assert rental_alerts_run(tmp_path, book=book(), today=date(2026, 11, 7), send=keep) == {"alerts": 0, "sent": False}
    assert rental_alerts_run(tmp_path, book=book(), today=date(2026, 11, 8), send=lambda t: False) == {"alerts": 1, "sent": False}
    assert rental_alerts_run(tmp_path, book=book(), today=date(2026, 11, 8), send=keep) == {"alerts": 1, "sent": True}
    assert rental_alerts_run(tmp_path, book=book(), today=date(2026, 11, 20), send=keep) == {"alerts": 0, "sent": False}
    assert rental_alerts_run(tmp_path, book=book(), today=date(2026, 12, 8), send=keep)["sent"] is True
    assert len(sent) == 2 and "Phòng 301" in sent[0] and "khuyến nghị" in sent[0]


def test_rent_not_collected_is_in_vic_can_xem(tmp_path):
    owner = OwnerContext("owner-1", "owner", "test")
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(owner, *RECORD, book().model_dump(mode="json"), expected_version=0, request_id="rb1")
    items = attention_items(repo, owner, tmp_path, now=datetime(2026, 11, 9, 3, tzinfo=timezone.utc))
    assert any(i["kind"] == "rent_due" and i["text"].startswith("Phòng 301: chưa thu đủ") and i["href"] == "/profile?tab=tai-san" for i in items)
