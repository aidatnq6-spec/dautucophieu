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
    assert [s.parent.name for s in skills] == ["dautu-ma", "dautu-quy", "dautu-sosanh", "dautu-thitruong", "dautu-vimo"]
    for skill in skills:
        text = skill.read_text(encoding="utf-8")
        assert text.startswith("---\n") and f"name: {skill.parent.name}\n" in text
        named = set(re.findall(r"`([a-z_]+)`", text))
        assert named and named <= tools | {"thieu"}, (skill.parent.name, named - tools)


def test_frontmatter_text_values_are_quoted_so_yaml_reads_them_as_strings():
    # An unquoted value holding ": " fails to parse and the skill loads with no name or description; one opening with "[" reads as a list.
    for skill in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
        head = skill.read_text(encoding="utf-8").split("---\n")[1]
        fields = dict(line.split(": ", 1) for line in head.strip().splitlines())
        assert set(fields) == {"name", "description", "argument-hint"}, skill.parent.name
        for key in ("description", "argument-hint"):
            value = fields[key]
            assert value.startswith('"') and value.endswith('"') and '"' not in value[1:-1].replace('\\"', ""), (skill.parent.name, key)


def test_chat_project_instructions_name_every_server_tool_and_nothing_else(tmp_path):
    # docs/claude-project-instructions.md is pasted into the Claude Desktop Chat project; a new tool must be added there too.
    text = (REPO / "docs" / "claude-project-instructions.md").read_text(encoding="utf-8")
    block = text.split("```text\n", 1)[1].split("\n```", 1)[0]
    tools = server_tools(tmp_path)
    named = set(re.findall(r"\b([a-z]+(?:_[a-z]+)+)\b", block)) - {"lay_luc", "fetched_at", "as_of", "ly_do", "tep_cap_nhat_luc", "so_ky", "npat_parent", "minority_equity", "pham_vi", "su_kien_co_phieu", "mat_do", "dieu_chinh", "dividends_paid", "canh_bao_loi_nhuan_ngoai_ban_hang", "vuot_nguong", "ten_chi_so", "luu_y", "phien_thieu", "canh_bao_eps", "thieu_so_luong", "van_ban", "lich_kiem"}
    named |= {t for t in tools if re.search(rf"\b{t}\b", block)}  # single-word tools such as omo
    assert named == tools, named ^ tools
    assert "dautucophieu-cong-khai" in block and "thieu" in block
