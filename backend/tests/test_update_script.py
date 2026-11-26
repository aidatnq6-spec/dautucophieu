"""update-app.ps1 keeps the running app on main's code, also after a merge made on this machine (26/11/2026).

That evening the app kept serving a 16:36 build while verify.ps1 had rebuilt apps/web/.next at 18:44 under it, and the merged commit
was already on origin/main, so update-app saw nothing new and never restarted: /research pages hung or failed to load.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "windows"


def code_lines(name):
    text = (SCRIPTS / name).read_text(encoding="utf-8-sig")
    return [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]


def deployed(web: Path, head: str) -> str:
    if shutil.which("powershell.exe") is None:
        pytest.skip("Windows PowerShell only")
    probe = web.parent / "probe.ps1"
    probe.write_text(f". '{SCRIPTS / 'common.ps1'}'\nTest-WebDeployed '{web}' '{head}'\n", encoding="utf-8")
    run = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(probe)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    return run.stdout.strip()


def test_the_web_build_counts_as_deployed_only_when_update_app_built_this_commit(tmp_path):
    web = tmp_path / "web"
    (web / ".next").mkdir(parents=True)
    assert deployed(web, "abc") == "False"  # built by someone else (verify.ps1, a manual build): the marker is gone
    (web / ".next" / "deployed-commit").write_text("abc\n", encoding="ascii")
    assert deployed(web, "abc") == "True"
    assert deployed(web, "def") == "False"  # merged on this machine: HEAD moved past what is running


def test_nothing_new_on_origin_still_rebuilds_and_restarts_when_the_build_is_not_this_commit():
    ls = code_lines("update-app.ps1")
    same = next(i for i, l in enumerate(ls) if l.startswith("if ($old -eq $new "))
    assert "Test-WebDeployed" in ls[same] and "return" in ls[same]
    build = next(i for i, l in enumerate(ls) if "Invoke-Native 'build'" in l)
    marker = next(i for i, l in enumerate(ls) if "deployed-commit" in l and "Set-Content" in l)
    restart = next(i for i, l in enumerate(ls) if "stop-app.ps1" in l)
    assert build < marker < restart
