from datetime import date
from decimal import Decimal

from investment_agent.api.auth import OwnerContext
from investment_agent.domain.journal import JournalEntry
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.journal import append_entry, read_journal, render_review, review_run

OWNER = OwnerContext("owner-1", "owner", "test")


def repo_with_entry():
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    append_entry(repo, OWNER, JournalEntry(entry_id="j1", symbol="HPG", kind="buy", created_on=date(2026, 10, 26), reason="Thép hồi phục",
                                           emotion="fomo", emotion_note="sợ lỡ sóng", context={"price": "20000"}), request_id="j1")
    return repo


def test_message_repeats_the_recorded_reason_and_emotion_without_advice():
    e = JournalEntry(entry_id="j1", symbol="HPG", kind="buy", created_on=date(2026, 10, 26), reason="Thép hồi phục", emotion="fomo",
                     emotion_note="sợ lỡ sóng", context={"price": "20000"})
    text = render_review([{"entry": e, "level": -1, "change": "-0.1600", "price": "16800"}])
    assert "HPG" in text and "Thép hồi phục" in text and "Sợ bỏ lỡ (FOMO)" in text and "sợ lỡ sóng" in text
    assert "−16,0%" in text and "20.000" in text and "16.800" in text and "26/10/2026" in text
    assert "nên" not in text.lower()  # a reminder of what was written, never a recommendation


def test_review_sends_once_per_level_and_records_it():
    repo, sent = repo_with_entry(), []
    out = review_run(repo, OWNER, prices={"HPG": Decimal("23500")}, threshold=Decimal("0.15"), send=lambda t: sent.append(t) or True, request_id="r1")
    assert out == {"due": 1, "sent": True} and len(sent) == 1
    assert read_journal(repo, OWNER)[0][0].reviewed_levels == (1,)
    out = review_run(repo, OWNER, prices={"HPG": Decimal("24000")}, threshold=Decimal("0.15"), send=lambda t: sent.append(t) or True, request_id="r2")
    assert out == {"due": 0, "sent": False} and len(sent) == 1


def test_a_failed_send_is_retried_next_time():
    repo = repo_with_entry()
    out = review_run(repo, OWNER, prices={"HPG": Decimal("23500")}, threshold=Decimal("0.15"), send=lambda t: False, request_id="r1")
    assert out == {"due": 1, "sent": False} and read_journal(repo, OWNER)[0][0].reviewed_levels == ()
