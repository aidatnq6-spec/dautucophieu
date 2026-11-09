from datetime import date

from investment_agent.api.auth import OwnerContext
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.accumulation import remind_run

OWNER = OwnerContext("owner-1", "owner", "test")
PLAN = {"id": "g", "name": "Vàng nhẫn", "asset": "gold", "day": 10, "start": "2026-11", "chi": "1"}


def repo_with(plans=(PLAN,)):
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(OWNER, "settings", "accumulation", {"plans": list(plans), "buys": []}, expected_version=0, request_id="p1")
    return repo


def test_reminds_once_a_month_per_plan_from_its_day_and_retries_a_failed_send():
    repo, sent = repo_with(), []
    keep = lambda t: sent.append(t) or True  # noqa: E731
    assert remind_run(repo, OWNER, today=date(2026, 11, 9), send=keep, request_id="r0") == {"due": 0, "sent": False}
    assert remind_run(repo, OWNER, today=date(2026, 11, 10), send=lambda t: False, request_id="r1") == {"due": 1, "sent": False}
    assert remind_run(repo, OWNER, today=date(2026, 11, 10), send=keep, request_id="r2") == {"due": 1, "sent": True}
    assert remind_run(repo, OWNER, today=date(2026, 11, 11), send=keep, request_id="r3") == {"due": 0, "sent": False}
    assert remind_run(repo, OWNER, today=date(2026, 12, 10), send=keep, request_id="r4") == {"due": 1, "sent": True}
    assert len(sent) == 2 and "Vàng nhẫn" in sent[0] and "1 chỉ" in sent[0] and "nên mua" not in sent[0].lower()


def test_no_plans_no_reminder():
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    assert remind_run(repo, OWNER, today=date(2026, 11, 10), send=lambda t: True, request_id="r1") == {"due": 0, "sent": False}


def test_attention_lines_name_a_plan_that_is_due():
    from investment_agent.services.accumulation import due_lines
    assert any("Vàng nhẫn" in x for x in due_lines(repo_with(), OWNER, today=date(2026, 11, 10), quotes={"gold": {}, "funds": {}}))
    assert due_lines(repo_with(), OWNER, today=date(2026, 11, 9), quotes={"gold": {}, "funds": {}}) == []
