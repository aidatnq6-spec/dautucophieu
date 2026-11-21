# Canh bao gia: Task Scheduler calls this every 5 minutes during trading hours; the command itself does nothing outside
# the session or when no level is armed, so most wake-ups call no source. One line per wake-up in logs\scheduler.log.
. (Join-Path $PSScriptRoot 'common.ps1')
$log = Join-Path $script:RepoRoot 'logs\scheduler.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
Import-LocalEnv
$python = Get-RepoPython
# Steps must not stop on a stderr line (Windows PowerShell 5.1 under 'Stop'); see run-after-close.ps1.
$ErrorActionPreference = 'Continue'
# Each step through investment_agent.jobs.step, stopped after 4 minutes so it never runs into the next wake-up.
$data = Join-Path $script:RepoRoot 'data'
$out = & $python -W ignore -m investment_agent.jobs.step --timeout 240 price-alerts --data-dir $data 2>$null
"$(Get-Date -Format o) price-alerts exit=$LASTEXITCODE $out" | Add-Content -LiteralPath $log -Encoding UTF8
# Luan diem dau tu: loss against cost for open theses, on the same wake-up (nothing is read outside the session).
$calendar = Join-Path $data 'trading-calendar.json'
if (-not (Test-Path -LiteralPath $calendar)) { $calendar = Join-Path $script:RepoRoot "config\trading-calendar-hose-$((Get-Date).Year).json" }
$tc = & $python -W ignore -m investment_agent.jobs.step --timeout 240 thesis-check --scope price --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) thesis-check-price exit=$LASTEXITCODE $tc" | Add-Content -LiteralPath $log -Encoding UTF8
# Tinh trang he thong: from this separate task, so an after-close run that stopped happening is still noticed.
$hc = & $python -W ignore -m investment_agent.jobs.step --timeout 240 health-check --data-dir $data 2>$null
"$(Get-Date -Format o) health-check exit=$LASTEXITCODE $hc" | Add-Content -LiteralPath $log -Encoding UTF8
