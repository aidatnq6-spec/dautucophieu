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


def test_contribution_reminder_runs_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.cli contribution-remind" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.cli scheduled-run" in l)


def test_deposit_reminder_runs_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.cli deposit-alerts" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.cli scheduled-run" in l)


def test_fund_navs_are_synced_on_every_wake_up():
    assert any("investment_agent.cli fund-nav-sync" in l for l in lines())


def test_thesis_lights_are_checked_on_every_wake_up():
    assert any("investment_agent.cli thesis-lights" in l for l in lines())


def test_receivable_sign_alerts_follow_the_statement_refresh():
    ls = lines()
    assert next(i for i, l in enumerate(ls) if "cli statements-sync" in l) < next(i for i, l in enumerate(ls) if "cli receivable-alerts" in l)


def test_source_alerts_follow_the_macro_update():
    ls = lines()
    assert next(i for i, l in enumerate(ls) if "cli macro-sync" in l) < next(i for i, l in enumerate(ls) if "cli source-alerts" in l)


def test_liquidity_alerts_follow_the_macro_update():
    ls = lines()
    assert next(i for i, l in enumerate(ls) if "cli macro-sync" in l) < next(i for i, l in enumerate(ls) if "cli liquidity-alerts" in l)


def test_macro_event_reminders_run_on_every_wake_up():
    assert any("investment_agent.cli macro-events-remind" in l for l in lines())


def test_the_buy_plan_is_checked_on_every_wake_up():
    assert any("investment_agent.cli buy-plan-check" in l for l in lines())


def test_fund_holdings_are_synced_after_the_navs():
    ls = lines()
    assert next(i for i, l in enumerate(ls) if "cli fund-nav-sync" in l) < next(i for i, l in enumerate(ls) if "cli fund-holdings-sync" in l)


def test_gold_prices_are_synced_on_every_wake_up():
    assert any("investment_agent.cli gold-price-sync" in l for l in lines())


def test_accumulation_reminder_runs_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.cli accumulation-remind" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.cli scheduled-run" in l)


# On 2026-11-21 the 06:08 logon run ended with exit 1 after "start" and logged no step: under common.ps1's
# $ErrorActionPreference = 'Stop', Windows PowerShell 5.1 turns any stderr line of a native command into a terminating
# NativeCommandError, even with 2>$null, so one warning from one step stopped every step after it.
def _continue_line(ls):
    return next(i for i, l in enumerate(ls) if l.replace(" ", "").lower() == "$erroractionpreference='continue'")


def test_steps_run_with_continue_after_the_setup_that_must_stop():
    ls = lines()
    at = _continue_line(ls)
    assert next(i for i, l in enumerate(ls) if l.startswith("$python = Get-RepoPython")) < at
    assert at < next(i for i, l in enumerate(ls) if "investment_agent.cli" in l)


def test_a_step_writing_to_stderr_does_not_stop_the_run(tmp_path):
    import shutil
    import subprocess
    import sys

    if shutil.which("powershell.exe") is None:
        import pytest
        pytest.skip("Windows PowerShell only")
    common = SCRIPT.parent / "common.ps1"
    probe = tmp_path / "probe.ps1"
    probe.write_text("\n".join([
        f". '{common}'",
        lines()[_continue_line(lines())],
        f"$out = & '{sys.executable}' -c \"import sys; sys.stderr.write('warn'); print('ok')\" 2>$null",
        "\"after exit=$LASTEXITCODE $out\"",
    ]), encoding="utf-8")
    run = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(probe)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    assert "after exit=0 ok" in run.stdout


def test_price_alert_steps_also_run_with_continue():
    alerts = SCRIPT.parent / "run-alerts.ps1"
    ls = [l.strip() for l in alerts.read_text(encoding="utf-8-sig").splitlines() if l.strip() and not l.strip().startswith("#")]
    at = _continue_line(ls)
    assert next(i for i, l in enumerate(ls) if l.startswith("$python = Get-RepoPython")) < at
    assert at < next(i for i, l in enumerate(ls) if "investment_agent.cli" in l)
