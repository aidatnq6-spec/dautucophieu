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


def main(argv: list[str]) -> int:
    timeout: float = DEFAULT_TIMEOUT
    if argv[:1] == ["--timeout"]:
        timeout, argv = int(argv[1]), argv[2:]
    out, code = run_step([sys.executable, "-W", "ignore", "-m", "investment_agent.cli", *argv], timeout=timeout)
    sys.stdout.write(out.encode("ascii", errors="backslashreplace").decode("ascii") + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
