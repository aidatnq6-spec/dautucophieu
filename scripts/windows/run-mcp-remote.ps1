# MCP du lieu cong khai tu xa (27/11/2026): serve the public tools over HTTP on 127.0.0.1:8770 for Tailscale Funnel.
# Started by the InvestmentAgent-McpRemote task at logon; without MCP_REMOTE_SECRET in .env.local it logs and stops.
. (Join-Path $PSScriptRoot 'common.ps1')
$log = Join-Path $script:RepoRoot 'logs\mcp-remote.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
Import-LocalEnv
# Steps must not stop on a stderr line (Windows PowerShell 5.1 under 'Stop'); see run-after-close.ps1.
$ErrorActionPreference = 'Continue'
if (-not $env:MCP_REMOTE_SECRET) { "$(Get-Date -Format o) skip: chua co MCP_REMOTE_SECRET trong .env.local" | Add-Content -LiteralPath $log -Encoding UTF8; return }
$python = Get-RepoPython
"$(Get-Date -Format o) start" | Add-Content -LiteralPath $log -Encoding UTF8
# The server writes its own UTF-8 log (warnings and errors); stderr is dropped, as PowerShell 5.1 turned it into UTF-16 error records.
& $python -W ignore -m investment_agent.mcp_remote 2>$null
"$(Get-Date -Format o) stop exit=$LASTEXITCODE" | Add-Content -LiteralPath $log -Encoding UTF8
