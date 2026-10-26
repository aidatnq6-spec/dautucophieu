from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.domain.journal import JournalEntry, add_note, due_reviews, mark_reviewed

CONTEXT = {"price": "20900", "pe": "9.8", "verdict": "cheap", "macd_d1": "up,>0", "rsi_d1": 55, "vnindex": "1763.55"}


def entry(**over):
    base = {"entry_id": "j1", "symbol": "HPG", "kind": "hold", "created_on": "2026-10-26", "reason": "Giá dưới giá trị sổ sách",
            "emotion": "calm", "emotion_note": "", "context": CONTEXT, "ledger_event_id": None, "notes": [], "reviewed_levels": []}
    return JournalEntry.model_validate({**base, **over})


def test_entry_keeps_reason_emotion_and_context_and_rejects_unknown_emotions():
    e = entry()
    assert e.reason == "Giá dưới giá trị sổ sách" and e.emotion == "calm" and e.context["verdict"] == "cheap"
    with pytest.raises(ValidationError):
        entry(emotion="ecstatic")
    with pytest.raises(ValidationError):
        entry(kind="short")


def test_notes_are_appended_never_rewriting_the_original():
    e = add_note(entry(), text="Giữ tiếp, KQKD quý III tốt", on="2026-11-10")
    assert e.reason == "Giá dưới giá trị sổ sách" and [n.text for n in e.notes] == ["Giữ tiếp, KQKD quý III tốt"]


def test_reviews_fire_each_time_the_price_moves_another_15_percent():
    e = entry()  # recorded at 20,900
    assert due_reviews([e], prices={"HPG": Decimal("23000")}, threshold=Decimal("0.15")) == []  # +10%
    due = due_reviews([e], prices={"HPG": Decimal("24100")}, threshold=Decimal("0.15"))  # +15.3%
    assert [(d["entry"].entry_id, d["level"], d["change"]) for d in due] == [("j1", 1, "0.1531")]
    e = mark_reviewed(e, level=1)
    assert due_reviews([e], prices={"HPG": Decimal("25000")}, threshold=Decimal("0.15")) == []  # still level 1
    assert due_reviews([e], prices={"HPG": Decimal("27500")}, threshold=Decimal("0.15"))[0]["level"] == 2  # +31.6%
    assert due_reviews([e], prices={"HPG": Decimal("17000")}, threshold=Decimal("0.15"))[0]["level"] == -1  # −18.7%


def test_no_price_or_no_recorded_price_means_no_review():
    assert due_reviews([entry()], prices={}, threshold=Decimal("0.15")) == []
    assert due_reviews([entry(context={})], prices={"HPG": Decimal("30000")}, threshold=Decimal("0.15")) == []
