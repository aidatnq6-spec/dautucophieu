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
    assert start < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step" in l)


def test_finish_is_logged_before_exit():
    ls = lines()
    assert "finish exit=" in ls[-2] and ls[-1] == "exit $runExit"


def test_market_snapshot_runs_before_the_brief_is_built():
    ls = lines()
    snap = next(i for i, l in enumerate(ls) if "investment_agent.jobs.step brief-snapshot" in l)
    assert snap < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step scheduled-run" in l)
    assert snap > next(i for i, l in enumerate(ls) if "investment_agent.jobs.step trend-run" in l)


def test_corporate_events_are_synced_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.jobs.step events-sync" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step scheduled-run" in l)


def test_journal_reviews_run_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.jobs.step journal-review" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step scheduled-run" in l)


def test_drawdown_check_runs_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.jobs.step --timeout 900 portfolio-alerts" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step scheduled-run" in l)


def test_contribution_reminder_runs_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.jobs.step wealth-alerts" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step scheduled-run" in l)


def test_deposit_reminder_runs_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.jobs.step wealth-alerts" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step scheduled-run" in l)


def test_the_tower_is_checked_after_prices_and_fund_navs_are_synced():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.jobs.step wealth-alerts" in l)
    assert step > next(i for i, l in enumerate(ls) if "market-sync --symbols" in l)
    assert step > next(i for i, l in enumerate(ls) if "investment_agent.jobs.step fund-nav-sync" in l)
    assert step > next(i for i, l in enumerate(ls) if "investment_agent.jobs.step gold-price-sync" in l)


def test_fund_navs_are_synced_on_every_wake_up():
    assert any("investment_agent.jobs.step fund-nav-sync" in l for l in lines())


def test_thesis_lights_are_checked_on_every_wake_up():
    assert any("investment_agent.jobs.step thesis-lights" in l for l in lines())


def test_receivable_sign_alerts_follow_the_statement_refresh():
    ls = lines()
    assert next(i for i, l in enumerate(ls) if "jobs.step statements-sync" in l) < next(i for i, l in enumerate(ls) if "jobs.step receivable-alerts" in l)


def test_source_alerts_follow_the_macro_update():
    ls = lines()
    assert next(i for i, l in enumerate(ls) if "jobs.step macro-sync" in l) < next(i for i, l in enumerate(ls) if "jobs.step source-alerts" in l)


def test_liquidity_alerts_follow_the_macro_update():
    """Nhắc thanh khoản và tỷ giá now goes out with the lights in one step, macro-alerts (owner, 21/11/2026)."""
    ls = lines()
    assert next(i for i, l in enumerate(ls) if "jobs.step macro-sync" in l) < next(i for i, l in enumerate(ls) if "jobs.step macro-alerts" in l)
    assert not any("jobs.step liquidity-alerts" in l or "jobs.step macro-signals" in l for l in ls)  # never two messages for one run


def test_macro_event_reminders_run_on_every_wake_up():
    assert any("investment_agent.jobs.step macro-events-remind" in l for l in lines())


def test_the_buy_plan_is_checked_on_every_wake_up():
    assert any("investment_agent.jobs.step --timeout 900 portfolio-alerts" in l for l in lines())


def test_fund_holdings_are_synced_after_the_navs():
    ls = lines()
    assert next(i for i, l in enumerate(ls) if "jobs.step fund-nav-sync" in l) < next(i for i, l in enumerate(ls) if "jobs.step fund-holdings-sync" in l)


def test_gold_prices_are_synced_on_every_wake_up():
    assert any("investment_agent.jobs.step gold-price-sync" in l for l in lines())


def test_accumulation_reminder_runs_on_every_wake_up():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.jobs.step wealth-alerts" in l)
    assert step < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step scheduled-run" in l)


# On 2026-11-21 the 06:08 logon run ended with exit 1 after "start" and logged no step: under common.ps1's
# $ErrorActionPreference = 'Stop', Windows PowerShell 5.1 turns any stderr line of a native command into a terminating
# NativeCommandError, even with 2>$null, so one warning from one step stopped every step after it.
def _continue_line(ls):
    return next(i for i, l in enumerate(ls) if l.replace(" ", "").lower() == "$erroractionpreference='continue'")


def test_steps_run_with_continue_after_the_setup_that_must_stop():
    ls = lines()
    at = _continue_line(ls)
    assert next(i for i, l in enumerate(ls) if l.startswith("$python = Get-RepoPython")) < at
    assert at < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step" in l)


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
    assert at < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step" in l)


# Every step goes through jobs.step (owner's choice, 21/11/2026): a time limit per step, and the last stderr line in the log.
def _script_lines(name):
    path = SCRIPT.parent / name
    return [l.strip() for l in path.read_text(encoding="utf-8-sig").splitlines() if l.strip() and not l.strip().startswith("#")]


def test_every_scheduled_step_runs_under_a_time_limit():
    for name in ("run-after-close.ps1", "run-alerts.ps1"):
        # the log's monthly move is a local file move with no source to wait on, so it is the one call outside the time limit
        calls = [l for l in _script_lines(name) if "& $python" in l and "investment_agent.jobs.log_rotate" not in l]
        assert calls and all("-m investment_agent.jobs.step " in l for l in calls), name
        assert not any("investment_agent.cli" in l for l in _script_lines(name)), name


def test_the_slow_market_sync_gets_fifteen_minutes_and_price_alerts_stop_before_the_next_wake_up():
    ls = lines()
    assert all("jobs.step --timeout 900 market-sync" in l for l in ls if "market-sync" in l and "& $python" in l)
    alerts = [l for l in _script_lines("run-alerts.ps1") if "& $python" in l]
    assert alerts and all("jobs.step --timeout 240 " in l for l in alerts)


def test_macro_signals_run_right_after_the_macro_sync():
    """Đèn tín hiệu rủi ro vĩ mô (spec 21/11/2026): the lights are read on the figures the macro sync just stored."""
    ls = lines()
    sync = next(i for i, l in enumerate(ls) if "jobs.step macro-sync" in l)
    step = next(i for i, l in enumerate(ls) if "jobs.step macro-alerts" in l)
    assert sync < step < next(i for i, l in enumerate(ls) if "jobs.step scheduled-run" in l)


# --- 21/11/2026: nhật ký gọn hơn ---
def test_the_log_is_moved_to_its_month_once_a_run_has_started_and_before_any_step():
    ls = lines()
    rot = next(i for i, l in enumerate(ls) if "investment_agent.jobs.log_rotate" in l)
    assert next(i for i, l in enumerate(ls) if "start pid=" in l) < rot < next(i for i, l in enumerate(ls) if "investment_agent.jobs.step" in l)


ALERTS = SCRIPT.with_name("run-alerts.ps1")


def test_the_five_minute_steps_are_quiet_and_log_only_what_they_print():
    text = ALERTS.read_text(encoding="utf-8-sig")
    for step in ("price-alerts", "thesis-check", "health-check"):
        call = next(l for l in text.splitlines() if f"investment_agent.jobs.step --timeout 240 --quiet {step}" in l)
        assert call.strip().startswith("$")
    assert text.count("if ($") >= 3 and "Add-Content" in text

def test_the_personal_reminders_go_out_as_one_step():
    ls = lines()
    assert sum("investment_agent.jobs.step wealth-alerts" in l for l in ls) == 1
    for old in ("deposit-alerts", "pyramid-alerts", "loan-alerts", "contribution-remind", "accumulation-remind"):
        assert not any(f"investment_agent.jobs.step {old}" in l for l in ls), old

def test_the_stock_reminders_go_out_as_one_step_after_the_data_they_read():
    ls = lines()
    step = next(i for i, l in enumerate(ls) if "investment_agent.jobs.step --timeout 900 portfolio-alerts --data-dir $data --calendar $calendar" in l)
    for before in ("statements-sync", "fundamentals-sync", "plans-sync", "events-sync", "gold-price-sync"):
        assert next(i for i, l in enumerate(ls) if f"investment_agent.jobs.step {before}" in l) < step, before
    for old in ("buy-plan-check", "insider-alerts", "drawdown-check", "thesis-check"):
        assert not any(f"investment_agent.jobs.step {old}" in l for l in ls), old

def test_company_notes_follow_the_bank_notes_owner_25_11_2026():
    """Both ask Vietcap; the company notes wait 10 s before their first call, after the bank notes."""
    ls = lines()
    assert next(i for i, l in enumerate(ls) if "jobs.step bank-notes-sync" in l) < next(i for i, l in enumerate(ls) if "jobs.step company-notes-sync" in l)
