# Canh bao gia: Task Scheduler calls this every 5 minutes during trading hours; the command itself does nothing outside
# the session or when no level is armed, so most wake-ups call no source. One line per wake-up in logs\scheduler.log.
. (Join-Path $PSScriptRoot 'common.ps1')
$log = Join-Path $script:RepoRoot 'logs\scheduler.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
Import-LocalEnv
$python = Get-RepoPython
$data = Join-Path $script:RepoRoot 'data'
$out = & $python -W ignore -m investment_agent.cli price-alerts --data-dir $data 2>$null
"$(Get-Date -Format o) price-alerts exit=$LASTEXITCODE $out" | Add-Content -LiteralPath $log -Encoding UTF8
