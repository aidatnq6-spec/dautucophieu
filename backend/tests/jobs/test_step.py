"""One scheduled step under a time limit, with the last stderr line kept for the log (owner's choice, 21/11/2026).

A step that hangs used to hold the whole wake-up until Task Scheduler stopped it at 30 minutes, leaving no "finish"; a step that failed
left only its exit code, so why it failed was lost."""

import json
import sys
import time

from investment_agent.jobs.step import TIMEOUT_EXIT, last_line, run_step


def py(code):
    return [sys.executable, "-c", code]


def test_the_step_passes_its_output_and_exit_code_through():
    out, code = run_step(py("import sys; print('{\"status\": \"ok\"}'); sys.exit(1)"), timeout=30)
    assert (out, code) == ('{"status": "ok"}', 1)


def test_the_last_stderr_line_is_added_quoted_so_one_log_line_stays_one_line():
    code_text = "import sys; print('{}'); sys.stderr.write('Traceback (most recent call last):\\n  File x\\nhttpx.ConnectError: lỗi DNS\\n\\n')"
    out, code = run_step(py(code_text), timeout=30)
    assert out == '{} stderr: "httpx.ConnectError: l\\u1ed7i DNS"' and code == 0


def test_a_step_over_its_limit_is_stopped_with_its_children_and_says_so():
    start = time.monotonic()
    child = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); time.sleep(60)"
    out, code = run_step(py(child), timeout=2)
    assert time.monotonic() - start < 20
    assert code == TIMEOUT_EXIT == 124
    assert json.loads(out) == {"status": "timeout", "seconds": 2}


def test_last_line_is_short_and_empty_when_nothing_was_written():
    assert last_line("") is None and last_line("\n  \n") is None
    assert len(last_line("x" * 1000)) == 300


# --- 21/11/2026: nhật ký gọn hơn ---
def test_a_five_minute_step_with_nothing_new_is_quiet_but_one_an_hour_is_kept():
    from datetime import datetime
    from investment_agent.jobs.step import quiet
    at = datetime(2026, 11, 21, 14, 35)
    for text in ('{"status": "skipped", "reason": "outside_session"}', '{"status": "ok", "triggered": 0, "sent": false, "armed": 0}',
                 '{"status": "ok", "open": 0, "closed": 0, "events": 0, "sent": false, "errors": []}',
                 '{"status": "ok", "problems": 2, "sent": false}'):
        assert quiet(text, 0, now=at) is True
        assert quiet(text, 0, now=at.replace(minute=2)) is False  # the first wake-up of the hour says the task is alive
    for text, code in (('{"status": "ok", "triggered": 1, "sent": true}', 0), ('{"status": "ok", "problems": 1, "new": 1, "recovered": 0, "sent": false}', 0),
                       ('{"status": "ok", "events": 0, "sent": false, "errors": ["HPG"]}', 0), ('{"status": "ok", "problems": 0, "sent": false}', 1),
                       ('{"status": "ok", "sent": false} stderr: "x"', 0), ('{"status": "timeout", "seconds": 240}', 124), ("not json", 0)):
        assert quiet(text, code, now=at) is False


def test_quiet_prints_nothing_for_a_quiet_step(capsys, monkeypatch):
    from investment_agent.jobs import step
    monkeypatch.setattr(step, "run_step", lambda command, timeout: ('{"status": "skipped", "reason": "outside_session"}', 0))
    monkeypatch.setattr(step, "_now", lambda: __import__("datetime").datetime(2026, 11, 21, 14, 35))
    assert step.main(["--timeout", "240", "--quiet", "price-alerts"]) == 0
    assert capsys.readouterr().out == ""
    assert step.main(["--timeout", "240", "price-alerts"]) == 0
    assert "outside_session" in capsys.readouterr().out