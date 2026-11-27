"""MCP dữ liệu công khai từ xa (owner, 27/11/2026, docs/superpowers/specs/2026-11-27-mcp-tu-xa-design.md).

The same read-only public tools as the stdio server (mcp_server.build_server), over streamable HTTP on 127.0.0.1, for claude.ai on the
web and the phone through Tailscale Funnel. Only /<secret>/mcp answers (and /<secret>/healthz for the check on this machine); any other
path is 404. Hosts other than this machine and the Funnel name are refused; at most `limit_per_minute` requests a minute, then 429.

    python -m investment_agent.mcp_remote               serve (needs MCP_REMOTE_SECRET and MCP_REMOTE_HOST in the environment)
    python -m investment_agent.mcp_remote --new-secret  write a new secret into .env.local without printing it
    python -m investment_agent.mcp_remote --url         print the connector address for the owner to paste into claude.ai
"""

import argparse
import os
import re
import secrets
import time
from collections import deque
from pathlib import Path
from typing import Callable

PORT = 8770
LIMIT_PER_MINUTE = 120
_SECRET = re.compile(r"^[A-Za-z0-9_-]{32,}$")
REPO_ROOT = Path(__file__).resolve().parents[3]


def remote_app(data_dir: Path | str | None, *, secret: str, host: str, limit_per_minute: int = LIMIT_PER_MINUTE,
               clock: Callable[[], float] = time.monotonic):
    if not _SECRET.fullmatch(secret or ""):
        raise ValueError("MCP_REMOTE_SECRET phải có ít nhất 32 ký tự chữ, số, - hoặc _.")
    from mcp.server.transport_security import TransportSecuritySettings

    from investment_agent.mcp_server import build_server
    hosts = [f"127.0.0.1:{PORT}", f"localhost:{PORT}", "127.0.0.1", "localhost"] + ([host] if host else [])
    inner = build_server(data_dir).streamable_http_app(
        streamable_http_path=f"/{secret}/mcp", stateless_http=True,
        transport_security=TransportSecuritySettings(allowed_hosts=hosts,
                                                     allowed_origins=["https://claude.ai", "https://claude.com"] + [f"https://{h}" for h in hosts]))
    seen: deque[float] = deque()
    health = f"/{secret}/healthz"

    async def reply(send, status: int, body: bytes) -> None:
        await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
        await send({"type": "http.response.body", "body": body})

    async def app(scope, receive, send):
        if scope["type"] != "http":
            return await inner(scope, receive, send)  # lifespan: the session manager starts and stops with the server
        now = clock()
        while seen and now - seen[0] >= 60:
            seen.popleft()
        if len(seen) >= limit_per_minute:
            return await reply(send, 429, "Quá nhiều lượt gọi, thử lại sau một phút.".encode())
        seen.append(now)
        if scope.get("path") == health:
            return await reply(send, 200, b"ok")
        return await inner(scope, receive, send)
    return app


def configure_logging(path: Path) -> None:
    """Warnings and errors only, UTF-8, into logs/mcp-remote.log: the SDK logs every call at INFO ("Terminating session: None"), which
    PowerShell 5.1 wrote as UTF-16 error records when it went through stderr (27/11/2026)."""
    import logging
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.setLevel(logging.WARNING)
    logging.getLogger().addHandler(handler)
    for name in ("mcp", "uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _env_file() -> Path:
    return REPO_ROOT / ".env.local"


def write_new_secret(env_file: Path) -> None:
    """A fresh secret into .env.local (MCP_REMOTE_SECRET line replaced or added); never printed."""
    lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.is_file() else []
    lines = [l for l in lines if not l.startswith("MCP_REMOTE_SECRET=")] + [f"MCP_REMOTE_SECRET={secrets.token_urlsafe(32)}"]
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mcp_remote")
    parser.add_argument("--new-secret", action="store_true")
    parser.add_argument("--url", action="store_true")
    args = parser.parse_args(argv)
    if args.new_secret:
        write_new_secret(_env_file())
        print("Đã ghi chuỗi bí mật mới vào .env.local (không in ra). Khởi động lại tác vụ InvestmentAgent-McpRemote và nhập lại địa chỉ connector.")
        return 0
    secret, host = os.environ.get("MCP_REMOTE_SECRET", ""), os.environ.get("MCP_REMOTE_HOST", "")
    if args.url:
        if not (secret and host):
            print("Chưa có MCP_REMOTE_SECRET hoặc MCP_REMOTE_HOST trong .env.local.")
            return 1
        print(f"https://{host}/{secret}/mcp")
        return 0
    import uvicorn
    configure_logging(REPO_ROOT / "logs" / "mcp-remote.log")
    uvicorn.run(remote_app(os.environ.get("INVESTMENT_DATA_DIR"), secret=secret, host=host), host="127.0.0.1", port=PORT, log_level="warning", log_config=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
