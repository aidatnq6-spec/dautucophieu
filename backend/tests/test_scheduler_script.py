"""The scheduled run logs that it started before anything that can stall, and logs when it finished.

On 2026-10-26 the 15:30 run was stopped by Windows (0xC000013A) before writing a single log line, so it left no trace.
"""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "windows" / "run-after-close.ps1"


def lines():
    return [l.strip() for l in SCRIPT.read_text(encoding="utf-8-sig").splitlines() if l.strip() and not l.strip().startswith("#")]


def test_start_is_logged_before_env_loading_and_any_step():
    ls = lines()
    start = next(i for i, l in enumerate(ls) if "start pid=" in l)
    assert start < next(i for i, l in enumerate(ls) if l.startswith("Import-LocalEnv"))
    assert start < next(i for i, l in enumerate(ls) if "investment_agent.cli" in l)


def test_finish_is_logged_before_exit():
    ls = lines()
    assert "finish exit=" in ls[-2] and ls[-1] == "exit $runExit"


def test_market_snapshot_runs_before_the_brief_is_built():
    ls = lines()
    snap = next(i for i, l in enumerate(ls) if "investment_agent.cli brief-snapshot" in l)
    assert snap < next(i for i, l in enumerate(ls) if "investment_agent.cli scheduled-run" in l)
    assert snap > next(i for i, l in enumerate(ls) if "investment_agent.cli trend-run" in l)


def test_corporate_events_are_synced_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.cli events-sync" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.cli scheduled-run" in l)


def test_journal_reviews_run_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.cli journal-review" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.cli scheduled-run" in l)


def test_drawdown_check_runs_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.cli drawdown-check" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.cli scheduled-run" in l)
