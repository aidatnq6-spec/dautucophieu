# One scheduler wake-up. Task Scheduler calls this at 17:30, 18:30, 20:00 and at logon (catch-up).
# Secrets come from .env.local; nothing secret is passed on the command line or written to the log.
. (Join-Path $PSScriptRoot 'common.ps1')
Import-LocalEnv
$python = Get-RepoPython
$data = Join-Path $script:RepoRoot 'data'
$log = Join-Path $script:RepoRoot 'logs\scheduler.log'
New-Item -ItemType Directory -Force -Path $data, (Split-Path $log) | Out-Null
$calendar = Join-Path $data 'trading-calendar.json'
if (-not (Test-Path -LiteralPath $calendar)) { $calendar = Join-Path $script:RepoRoot "config\trading-calendar-hose-$((Get-Date).Year).json" }
$summary = & $python -W ignore -m investment_agent.cli scheduled-run --calendar $calendar --data-dir $data 2>$null
"$(Get-Date -Format o) exit=$LASTEXITCODE $summary" | Add-Content -LiteralPath $log -Encoding UTF8
exit $LASTEXITCODE
