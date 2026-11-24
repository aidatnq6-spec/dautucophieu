from datetime import date, datetime

from investment_agent.api.auth import OwnerContext
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.giveback import attention_lines, giveback_run, render_note, write_goals

OWNER = OwnerContext("owner-1", "owner", "test")
TODAY = date(2026, 10, 20)


def repo_holding_fpt(thresholds=True):
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(OWNER, "ledger_events", "main", {"events": [
        {"event_id": "d1", "type": "deposit", "effective_at": "2026-10-01", "sequence": 0, "amount": "500000000"},
        {"event_id": "b1", "type": "buy", "effective_at": "2026-10-02", "sequence": 0, "security_id": "FPT", "quantity": 1000, "price": "50000",
         "fee": "0", "tax": "0"}], "amendments": []}, expected_version=0, request_id="l1")
    if thresholds:
        repo.write(OWNER, "settings", "portfolio", {"concentration_limit": "0.25", "journal_review_threshold": "0.15", "drawdown_threshold": "0.3",
                                                    "giveback_min_gain": "0.3", "giveback_share": "0.5"}, expected_version=0, request_id="s1")
    return repo


def closes(tmp_path, values):
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(2026, 10, 2 + i), v) for i, v in enumerate(values)])


def test_the_note_gives_the_figures_and_dates_without_advice():
    row = {"symbol": "FPT", "since": "2026-10-02", "peak": {"gain": "20000000", "ratio": "0.4000", "on": "2026-10-03"},
           "now": {"gain": "5000000", "ratio": "0.1000", "on": "2026-10-05"}, "given_back": "15000000", "share": "0.7500"}
    goal = {"kind": "enough", "goal": {"id": "g1", "name": "Mua nhà", "amount": "70000000", "basis": "value"},
            "status": {"enough": True, "since": "2026-10-03", "days": 2}}
    text = render_note([row], [goal], reasons={"FPT": "Lợi nhuận tăng đều"})
    assert "FPT" in text and "20.000.000" in text and "03/10/2026" in text and "75,0%" in text and "15.000.000" in text
    assert "Lợi nhuận tăng đều" in text and "Mua nhà" in text and "70.000.000" in text
    assert "nên" not in text.lower()


def test_a_run_reminds_once_and_remembers_it(tmp_path):
    repo = repo_holding_fpt()
    closes(tmp_path, ["50", "70", "55"])
    sent = []
    out = giveback_run(repo, OWNER, tmp_path, send=lambda t: sent.append(t) or True, request_id="r1", today=TODAY)
    assert out == {"holdings": 1, "goals": 0, "sent": True} and "FPT" in sent[0]
    again = giveback_run(repo, OWNER, tmp_path, send=lambda t: sent.append(t) or True, request_id="r2", today=TODAY)
    assert again == {"holdings": 0, "goals": 0, "sent": False} and len(sent) == 1


def test_a_failed_send_is_tried_again_and_no_thresholds_means_no_reminder(tmp_path):
    repo = repo_holding_fpt()
    closes(tmp_path, ["50", "70", "55"])
    assert giveback_run(repo, OWNER, tmp_path, send=lambda t: False, request_id="r1", today=TODAY)["sent"] is False
    assert giveback_run(repo, OWNER, tmp_path, send=lambda t: True, request_id="r2", today=TODAY) == {"holdings": 1, "goals": 0, "sent": True}
    plain = repo_holding_fpt(thresholds=False)
    assert giveback_run(plain, OWNER, tmp_path, send=lambda t: True, request_id="r3", today=TODAY) == {"holdings": 0, "goals": 0, "sent": False}


def test_a_goal_is_reminded_when_it_becomes_covered_and_shows_in_attention(tmp_path):
    repo = repo_holding_fpt(thresholds=False)
    closes(tmp_path, ["50", "55"])
    write_goals(repo, OWNER, [{"id": "g1", "name": "Mua xe", "amount": "60000000", "basis": "value", "created_on": "2026-10-01", "closed": None}],
                expected_version=0, request_id="g1")
    sent = []
    assert giveback_run(repo, OWNER, tmp_path, send=lambda t: sent.append(t) or True, request_id="r1", today=TODAY)["goals"] == 0
    assert attention_lines(repo, OWNER, tmp_path, today=TODAY) == []
    closes(tmp_path, ["50", "55", "62"])
    assert giveback_run(repo, OWNER, tmp_path, send=lambda t: sent.append(t) or True, request_id="r2", today=TODAY)["goals"] == 1
    assert "Mua xe" in sent[-1]
    lines = attention_lines(repo, OWNER, tmp_path, today=TODAY)
    assert lines == [("goal", None, "Mục tiêu «Mua xe» đã đủ tiền từ 04/10/2026, theo giá trị danh mục.")]


def test_attention_lists_a_holding_past_both_thresholds(tmp_path):
    repo = repo_holding_fpt()
    closes(tmp_path, ["50", "70", "55"])
    lines = attention_lines(repo, OWNER, tmp_path, today=TODAY)
    assert lines == [("giveback", "FPT", "FPT: đã trả lại 75,0% lãi cao nhất (20.000.000 đ ngày 03/10/2026), lãi hôm nay 5.000.000 đ.")]
