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
