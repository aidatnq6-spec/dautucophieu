# One scheduler wake-up. Task Scheduler calls this at 08:30, 15:30, 20:00 and at logon (catch-up).
# Secrets come from .env.local; nothing secret is passed on the command line or written to the log.
. (Join-Path $PSScriptRoot 'common.ps1')
$log = Join-Path $script:RepoRoot 'logs\scheduler.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
# First line of every wake-up, before anything that can stall: a run stopped early still leaves a trace.
"$(Get-Date -Format o) start pid=$PID" | Add-Content -LiteralPath $log -Encoding UTF8
Import-LocalEnv
$python = Get-RepoPython
$data = Join-Path $script:RepoRoot 'data'
New-Item -ItemType Directory -Force -Path $data | Out-Null
$calendar = Join-Path $data 'trading-calendar.json'
if (-not (Test-Path -LiteralPath $calendar)) { $calendar = Join-Path $script:RepoRoot "config\trading-calendar-hose-$((Get-Date).Year).json" }
$symbols = Join-Path $data 'market-symbols.txt'
# Index constituents and sectors change a few times a year; refresh the VN30/VN100 labels and ICB sectors weekly.
$weekAgo = (Get-Date).AddDays(-7)
$groups = Join-Path $data 'index-groups.json'
if ((Test-Path -LiteralPath $symbols) -and (-not (Test-Path -LiteralPath $groups) -or (Get-Item -LiteralPath $groups).LastWriteTime -lt $weekAgo)) {
    $refresh = & $python -W ignore -m investment_agent.cli index-groups --output $groups 2>$null
    "$(Get-Date -Format o) index-groups exit=$LASTEXITCODE $refresh" | Add-Content -LiteralPath $log -Encoding UTF8
}
$sectors = Join-Path $data 'industries.json'
if ((Test-Path -LiteralPath $symbols) -and (-not (Test-Path -LiteralPath $sectors) -or (Get-Item -LiteralPath $sectors).LastWriteTime -lt $weekAgo)) {
    $refresh = & $python -W ignore -m investment_agent.cli industries --symbols "@$symbols" --output $sectors 2>$null
    "$(Get-Date -Format o) industries exit=$LASTEXITCODE $refresh" | Add-Content -LiteralPath $log -Encoding UTF8
}
if (Test-Path -LiteralPath $symbols) {
    $sync = & $python -W ignore -m investment_agent.cli market-sync --symbols "@$symbols" --data-dir $data --calendar $calendar --days 10 2>$null
    "$(Get-Date -Format o) market-sync exit=$LASTEXITCODE $sync" | Add-Content -LiteralPath $log -Encoding UTF8
    $sync = & $python -W ignore -m investment_agent.cli market-sync --symbols VNINDEX --index --data-dir $data --calendar $calendar --days 10 2>$null
    "$(Get-Date -Format o) market-sync VNINDEX exit=$LASTEXITCODE $sync" | Add-Content -LiteralPath $log -Encoding UTF8
}
# Public macro feeds (FRED, Vietcombank); a failing source is logged and the run continues.
$macro = & $python -W ignore -m investment_agent.cli macro-sync --data-dir $data 2>$null
"$(Get-Date -Format o) macro-sync exit=$LASTEXITCODE $macro" | Add-Content -LiteralPath $log -Encoding UTF8
# Dinh gia chi so: daily P/E and P/B of VNINDEX and VN30 from VNDirect's public API (whole history once, then the last 14 days).
$ivs = & $python -W ignore -m investment_agent.cli index-valuation-sync --data-dir $data 2>$null
"$(Get-Date -Format o) index-valuation-sync exit=$LASTEXITCODE $ivs" | Add-Content -LiteralPath $log -Encoding UTF8
# Chat luong bao cao: quarterly ratios of watched banks, securities firms and insurers (VNDirect public API), one call each.
$frs = & $python -W ignore -m investment_agent.cli financial-ratios-sync --data-dir $data 2>$null
"$(Get-Date -Format o) financial-ratios-sync exit=$LASTEXITCODE $frs" | Add-Content -LiteralPath $log -Encoding UTF8
# CAPM hint: beta of every watched ticker (VNDirect public API), one call.
$bs = & $python -W ignore -m investment_agent.cli beta-sync --data-dir $data 2>$null
"$(Get-Date -Format o) beta-sync exit=$LASTEXITCODE $bs" | Add-Content -LiteralPath $log -Encoding UTF8
# CAPM default ERP: Damodaran (NYU Stern) for Vietnam, read at most weekly.
$es = & $python -W ignore -m investment_agent.cli erp-sync --data-dir $data 2>$null
"$(Get-Date -Format o) erp-sync exit=$LASTEXITCODE $es" | Add-Content -LiteralPath $log -Encoding UTF8
# Giao dich noi bo moi: Telegram note for held tickers' new insider notices (only when scheduled delivery is on).
$ia = & $python -W ignore -m investment_agent.cli insider-alerts --data-dir $data 2>$null
"$(Get-Date -Format o) insider-alerts exit=$LASTEXITCODE $ia" | Add-Content -LiteralPath $log -Encoding UTF8
# Ban tin tuan: weekend runs only, once per week (only when scheduled delivery is on).
$wb = & $python -W ignore -m investment_agent.cli weekly-brief --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) weekly-brief exit=$LASTEXITCODE $wb" | Add-Content -LiteralPath $log -Encoding UTF8
# Public research reports (ACBS, World Bank): AI reads public report text only; at most 3 new reports, once per 6 hours.
$ins = & $python -W ignore -m investment_agent.cli insights-run --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) insights-run exit=$LASTEXITCODE $ins" | Add-Content -LiteralPath $log -Encoding UTF8
# Xu hướng board (MACD/RSI over M, W, D1, H4, H1) from 15:30 on trading days; skips itself otherwise.
$trend = & $python -W ignore -m investment_agent.cli trend-run --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) trend-run exit=$LASTEXITCODE $trend" | Add-Content -LiteralPath $log -Encoding UTF8
# Public market snapshot of the latest session for the brief (whole-HOSE board, indices, HOSE statistics, news RSS).
$brief = & $python -W ignore -m investment_agent.cli brief-snapshot --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) brief-snapshot exit=$LASTEXITCODE $brief" | Add-Content -LiteralPath $log -Encoding UTF8
# Corporate events of watched tickers (dividends, issues, shareholder meetings): refreshed daily, reminder 5 days ahead.
$events = & $python -W ignore -m investment_agent.cli events-sync --data-dir $data 2>$null
"$(Get-Date -Format o) events-sync exit=$LASTEXITCODE $events" | Add-Content -LiteralPath $log -Encoding UTF8
# Nhat ky: remind what was written when a journalled ticker moved another 15% (threshold in Cai dat).
$journal = & $python -W ignore -m investment_agent.cli journal-review --data-dir $data 2>$null
"$(Get-Date -Format o) journal-review exit=$LASTEXITCODE $journal" | Add-Content -LiteralPath $log -Encoding UTF8
# Ke hoach sut giam: full price history once per ticker, then a reminder when a holding falls past the threshold below cost.
$drawdown = & $python -W ignore -m investment_agent.cli drawdown-check --data-dir $data 2>$null
"$(Get-Date -Format o) drawdown-check exit=$LASTEXITCODE $drawdown" | Add-Content -LiteralPath $log -Encoding UTF8
# Gop von deu: once a month from the contribution day, while this month's deposits are below the plan.
$contrib = & $python -W ignore -m investment_agent.cli contribution-remind --data-dir $data 2>$null
"$(Get-Date -Format o) contribution-remind exit=$LASTEXITCODE $contrib" | Add-Content -LiteralPath $log -Encoding UTF8
# Statements for the Định giá page: from the 20:00 slot, refresh the 8 stalest tickers (about 3 minutes, paced for Vnstock's limit).
if ((Get-Date).Hour -ge 20) {
    $fund = & $python -W ignore -m investment_agent.cli fundamentals-sync --data-dir $data --limit 8 2>$null
    "$(Get-Date -Format o) fundamentals-sync exit=$LASTEXITCODE $fund" | Add-Content -LiteralPath $log -Encoding UTF8
    # Bao cao quy moi: Telegram note for tickers whose new quarter the sync just found (only when scheduled delivery is on).
    $qa = & $python -W ignore -m investment_agent.cli quarter-alerts --data-dir $data 2>$null
    "$(Get-Date -Format o) quarter-alerts exit=$LASTEXITCODE $qa" | Add-Content -LiteralPath $log -Encoding UTF8
}
$summary = & $python -W ignore -m investment_agent.cli scheduled-run --calendar $calendar --data-dir $data 2>$null
$runExit = $LASTEXITCODE
"$(Get-Date -Format o) exit=$runExit $summary" | Add-Content -LiteralPath $log -Encoding UTF8
# At most one backup per day, after the evening slot (or as a catch-up); retention prunes old ones.
$backup = & $python -W ignore -m investment_agent.cli backup --kind auto --data-dir $data --backup-dir (Join-Path $script:RepoRoot 'backups') 2>$null
"$(Get-Date -Format o) backup exit=$LASTEXITCODE $backup" | Add-Content -LiteralPath $log -Encoding UTF8
"$(Get-Date -Format o) finish exit=$runExit pid=$PID" | Add-Content -LiteralPath $log -Encoding UTF8
exit $runExit
