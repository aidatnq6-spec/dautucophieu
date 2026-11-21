"""One step of a scheduled wake-up: `python -m investment_agent.jobs.step [--timeout S] <cli command> [args]` runs
`python -m investment_agent.cli <cli command> [args]` and prints what it printed, on one line for scheduler.log.

- Over its time limit (default 600 s) the step is stopped with every process it started, prints {"status": "timeout", "seconds": S}
  and exits 124, so one hung step no longer holds the wake-up until Task Scheduler stops it (30 minutes) with no "finish" logged.
- The last non-empty stderr line (an exception's name and message, not "Traceback …") is added as `stderr: "…"`, JSON-quoted and
  at most 300 characters, so the log says why a step failed. The log stays on this computer (logs/ is never committed).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime

DEFAULT_TIMEOUT = 600
TIMEOUT_EXIT = 124
MAX_STDERR = 300


def last_line(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1][:MAX_STDERR] if lines else None


def _stop_tree(process: subprocess.Popen) -> None:
    if sys.platform == "win32":  # the venv's python.exe is a launcher: its child interpreter must go too
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
    else:
        process.kill()


def run_step(command: list[str], *, timeout: float) -> tuple[str, int]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # a pipe would get the Windows code page, which has no Vietnamese letters
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _stop_tree(process)
        process.communicate()
        return json.dumps({"status": "timeout", "seconds": timeout}), TIMEOUT_EXIT
    text = " ".join(out.decode("utf-8", errors="replace").splitlines()).strip()
    tail = last_line(err.decode("utf-8", errors="replace"))
    if tail:
        text = f"{text} stderr: {json.dumps(tail)}".strip()
    return text, process.returncode


COUNTS = ("triggered", "events", "new", "recovered")


def quiet(text: str, code: int, *, now: datetime) -> bool:
    """A five-minute step with nothing new to log (owner, 21/11/2026): exit 0, no stderr, nothing sent, triggered or newly wrong, no
    errors. The first wake-up of each hour is always kept, so the log still shows the task is alive."""
    if code != 0 or now.minute < 5 or " stderr: " in text:
        return False
    try:
        out = json.loads(text)
    except ValueError:
        return False
    if not isinstance(out, dict) or out.get("status") not in ("ok", "skipped") or out.get("sent") is True or out.get("errors"):
        return False
    if out.get("status") == "skipped":
        return out.get("reason") == "outside_session"
    return all(not out.get(k) for k in COUNTS)


def _now() -> datetime:
    return datetime.now()


def main(argv: list[str]) -> int:
    timeout: float = DEFAULT_TIMEOUT
    if argv[:1] == ["--timeout"]:
        timeout, argv = int(argv[1]), argv[2:]
    hush = argv[:1] == ["--quiet"]  # a five-minute step: print nothing when there is nothing new, so nothing is logged
    if hush:
        argv = argv[1:]
    out, code = run_step([sys.executable, "-W", "ignore", "-m", "investment_agent.cli", *argv], timeout=timeout)
    if hush and quiet(out, code, now=_now()):
        return code
    sys.stdout.write(out.encode("ascii", errors="backslashreplace").decode("ascii") + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
