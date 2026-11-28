# Restart the remote MCP (InvestmentAgent-McpRemote, 127.0.0.1:8770) so claude.ai serves the code update-app.ps1 just deployed (28/11/2026).
# A machine without the task, or with it disabled, is skipped; run-mcp-remote.ps1 itself stops when MCP_REMOTE_SECRET is not set.
. (Join-Path $PSScriptRoot 'common.ps1')
$task = Get-ScheduledTask -TaskName 'InvestmentAgent-McpRemote' -ErrorAction SilentlyContinue
if ($null -eq $task) { Write-Host 'skip no-task'; exit 0 }
if ($task.State -eq 'Disabled') { Write-Host 'skip disabled'; return }
Stop-ScheduledTask -TaskName 'InvestmentAgent-McpRemote' -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
# The venv launcher's python.exe keeps a child that may outlive the task's stop: end every server of this repository's code.
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'investment_agent\.mcp_remote' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-ScheduledTask -TaskName 'InvestmentAgent-McpRemote'
Write-Host 'restarted'
exit 0
