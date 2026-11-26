"""Plugin dautucophieu: manifest, local marketplace, bundled MCP server, and slash commands that name only the server's tools."""

import json
import re
from pathlib import Path

import anyio

from investment_agent.mcp_server import build_server

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins" / "dautucophieu"


def server_tools(tmp_path) -> set[str]:
    async def run():
        return {t.name for t in await build_server(tmp_path).list_tools()}
    return anyio.run(run)


def test_marketplace_lists_the_plugin_from_this_repo():
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert market["name"] == "dautucophieu"
    assert [(p["name"], p["source"]) for p in market["plugins"]] == [("dautucophieu", "./plugins/dautucophieu")]


def test_manifest_names_no_email_and_bundles_the_public_data_server():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "dautucophieu" and "email" not in json.dumps(manifest)
    servers = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    assert list(servers) == ["dautucophieu-cong-khai"]
    assert servers["dautucophieu-cong-khai"]["args"] == ["-m", "investment_agent.mcp_server"]
    assert "env" not in servers["dautucophieu-cong-khai"]  # no secret ever reaches the server
    assert not (REPO / ".mcp.json").exists()  # the plugin is the only registration, so the tools are not listed twice


def test_each_command_names_only_tools_the_server_has(tmp_path):
    tools = server_tools(tmp_path)
    skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    assert [s.parent.name for s in skills] == ["dautu-ma", "dautu-thitruong", "dautu-vimo"]
    for skill in skills:
        text = skill.read_text(encoding="utf-8")
        assert text.startswith("---\n") and f"name: {skill.parent.name}\n" in text
        named = set(re.findall(r"`([a-z_]+)`", text))
        assert named and named <= tools | {"thieu"}, (skill.parent.name, named - tools)
