from datetime import date

from investment_agent.api.auth import OwnerContext
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.contributions import remind_run, render_reminder

OWNER = OwnerContext("owner-1", "owner", "test")


def repo_with_plan():
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(OWNER, "ledger_events", "main", {"events": [
        {"event_id": "d1", "type": "deposit", "effective_at": "2026-11-10", "sequence": 0, "amount": "8000000"},
        {"event_id": "d2", "type": "deposit", "effective_at": "2026-12-03", "sequence": 0, "amount": "3000000"}], "amendments": []},
        expected_version=0, request_id="l1")
    repo.write(OWNER, "settings", "contribution_plan", {"amount": "8000000", "day": 10, "start": "2026-11"}, expected_version=0, request_id="p1")
    return repo


def test_message_states_the_month_the_gap_and_the_streak_without_advice():
    text = render_reminder("2026-12", net="3000000", amount="8000000", streak=1)
    assert "12/2026" in text and "3.000.000" in text and "8.000.000" in text and "5.000.000" in text and "1 tháng" in text
    assert "nên mua" not in text.lower()


def test_reminds_once_a_month_from_the_day_and_retries_a_failed_send():
    repo, sent = repo_with_plan(), []
    assert remind_run(repo, OWNER, today=date(2026, 12, 9), send=lambda t: sent.append(t) or True, request_id="r0") == {"due": None, "sent": False}
    assert remind_run(repo, OWNER, today=date(2026, 12, 10), send=lambda t: False, request_id="r1") == {"due": "2026-12", "sent": False}
    assert remind_run(repo, OWNER, today=date(2026, 12, 10), send=lambda t: sent.append(t) or True, request_id="r2") == {"due": "2026-12", "sent": True}
    assert remind_run(repo, OWNER, today=date(2026, 12, 11), send=lambda t: sent.append(t) or True, request_id="r3") == {"due": None, "sent": False}
    assert len(sent) == 1


def test_no_plan_no_reminder():
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    assert remind_run(repo, OWNER, today=date(2026, 12, 10), send=lambda t: True, request_id="r1") == {"due": None, "sent": False}
