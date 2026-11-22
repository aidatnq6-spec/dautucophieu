from datetime import date

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.domain.year_goals import GoalError
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.year_end import goals_remind_run, goals_view, save_goals

OWNER = OwnerContext("owner-1", "owner", "test")


def repo_with_deposits():
    r = PersonalRepository("owner-1", MemoryDocumentStore())
    r.write(OWNER, "ledger_events", "main", {"events": [
        {"event_id": "d0", "type": "deposit", "effective_at": "2026-12-20", "sequence": 0, "amount": "999"},
        {"event_id": "d1", "type": "deposit", "effective_at": "2027-02-03", "sequence": 0, "amount": "30000000"}], "amendments": []},
        expected_version=0, request_id="l1")
    return r


def test_goals_are_saved_per_year_and_read_against_the_years_figures():
    r = repo_with_deposits()
    assert goals_view(r, OWNER, year=2027, today=date(2027, 7, 2), data_dir=None, quotes={}) == {"year": 2027, "version": 0, "goals": None, "progress": None}
    out = save_goals(r, OWNER, year=2027, raw={"contribution": "120000000"}, expected_version=0, request_id="g1", today=date(2027, 7, 2),
                     data_dir=None, quotes={})
    assert out["version"] == 1 and out["goals"] == {"contribution": "120000000"}
    row = out["progress"]["rows"][0]
    assert row["now"] == "30000000" and row["share"] == "0.2500" and row["behind"] is True  # only 2027's deposits count
    with pytest.raises(GoalError):
        save_goals(r, OWNER, year=2027, raw={}, expected_version=1, request_id="g2", today=date(2027, 7, 2), data_dir=None, quotes={})


def test_one_line_a_month_from_the_first_while_a_goal_is_behind():
    r, sent = repo_with_deposits(), []
    keep = lambda t: sent.append(t) or True  # noqa: E731
    save_goals(r, OWNER, year=2027, raw={"contribution": "120000000"}, expected_version=0, request_id="g1", today=date(2027, 7, 2),
               data_dir=None, quotes={})
    assert goals_remind_run(r, OWNER, today=date(2027, 7, 1), send=lambda t: False, request_id="a", data_dir=None, quotes={})["sent"] is False
    assert goals_remind_run(r, OWNER, today=date(2027, 7, 2), send=keep, request_id="b", data_dir=None, quotes={})["sent"] is True
    assert goals_remind_run(r, OWNER, today=date(2027, 7, 9), send=keep, request_id="c", data_dir=None, quotes={})["sent"] is False
    assert sent == ["Mục tiêu 2027: tiền góp cả năm đạt 25% mục tiêu, tiến độ đều theo thời gian là 50%. So sánh, không phải dự báo."]
    on_track = PersonalRepository("owner-1", MemoryDocumentStore())
    assert goals_remind_run(on_track, OWNER, today=date(2027, 7, 2), send=keep, request_id="d", data_dir=None, quotes={})["sent"] is False
