"""MCP dữ liệu công khai từ xa (owner, 27/11/2026): the same public tools over HTTP behind a secret path, a host check and a rate limit."""

import json

import pytest
from starlette.testclient import TestClient

from investment_agent.mcp_remote import remote_app

SECRET = "s" * 40
HOST = "may.tail1234.ts.net"
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}}
HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json", "host": HOST}


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def client(tmp_path, **kw):
    return TestClient(remote_app(tmp_path, secret=SECRET, host=HOST, **kw), base_url=f"https://{HOST}")


def test_the_public_tools_answer_on_the_secret_path_only(tmp_path):
    with client(tmp_path) as c:
        ok = c.post(f"/{SECRET}/mcp", headers=HEADERS, content=json.dumps(INIT))
        assert ok.status_code == 200 and "dautucophieu" in ok.text.lower()
        assert c.post("/mcp", headers=HEADERS, content=json.dumps(INIT)).status_code == 404
        assert c.post(f"/{'x' * 40}/mcp", headers=HEADERS, content=json.dumps(INIT)).status_code == 404
        assert c.get(f"/{SECRET}/healthz", headers={"host": HOST}).text == "ok"
        assert c.get("/healthz", headers={"host": HOST}).status_code == 404


def test_another_host_is_refused(tmp_path):
    with client(tmp_path) as c:
        bad = c.post(f"/{SECRET}/mcp", headers={**HEADERS, "host": "evil.example.com"}, content=json.dumps(INIT))
        assert bad.status_code in (400, 403, 421)


def test_over_the_rate_limit_is_refused_until_the_minute_passes(tmp_path):
    clock = Clock()
    with client(tmp_path, limit_per_minute=3, clock=clock) as c:
        codes = [c.get(f"/{SECRET}/healthz", headers={"host": HOST}).status_code for _ in range(4)]
        assert codes == [200, 200, 200, 429]
        clock.t = 61.0
        assert c.get(f"/{SECRET}/healthz", headers={"host": HOST}).status_code == 200


@pytest.mark.parametrize("secret", ["", "short", "a b" * 20])
def test_a_missing_or_weak_secret_never_serves(tmp_path, secret):
    with pytest.raises(ValueError):
        remote_app(tmp_path, secret=secret, host=HOST)


def test_a_new_secret_goes_into_env_local_without_being_printed(tmp_path, capsys):
    from investment_agent.mcp_remote import write_new_secret
    env = tmp_path / ".env.local"
    env.write_text("TELEGRAM_BOT_TOKEN=keep\nMCP_REMOTE_SECRET=old\n", encoding="utf-8")
    write_new_secret(env)
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "TELEGRAM_BOT_TOKEN=keep" and sum(l.startswith("MCP_REMOTE_SECRET=") for l in lines) == 1
    new = next(l for l in lines if l.startswith("MCP_REMOTE_SECRET="))[len("MCP_REMOTE_SECRET="):]
    assert new != "old" and len(new) >= 32 and new not in capsys.readouterr().out


def test_a_windows_task_starts_the_remote_server_at_logon_and_restarts_it():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "scripts" / "windows"
    run = (root / "run-mcp-remote.ps1").read_text(encoding="utf-8-sig")
    assert "Import-LocalEnv" in run and "investment_agent.mcp_remote" in run and "MCP_REMOTE_SECRET" in run
    tasks = (root / "register-tasks.ps1").read_text(encoding="utf-8-sig")
    assert "InvestmentAgent-McpRemote" in tasks and "run-mcp-remote.ps1" in tasks and "-RestartCount" in tasks
    assert "$mcpName" in tasks.split("if ($Unregister)")[1].split("return")[0]  # unregistered with the others
