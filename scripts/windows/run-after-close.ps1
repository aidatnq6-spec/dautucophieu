# One scheduler wake-up. Task Scheduler calls this at 08:30, 15:30, 20:00 and at logon (catch-up).
# Secrets come from .env.local; nothing secret is passed on the command line or written to the log.
. (Join-Path $PSScriptRoot 'common.ps1')
$log = Join-Path $script:RepoRoot 'logs\scheduler.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
# First line of every wake-up, before anything that can stall: a run stopped early still leaves a trace.
"$(Get-Date -Format o) start pid=$PID" | Add-Content -LiteralPath $log -Encoding UTF8
Import-LocalEnv
$python = Get-RepoPython
# Each step runs through investment_agent.jobs.step: at most 10 minutes (market-sync 15), and its last stderr line is logged.
# The setup above stops on error; the steps below must not. Under 'Stop', Windows PowerShell 5.1 turns any stderr line of a step
# into a terminating error even with 2>$null, so one warning stopped every later step unlogged (06:08 logon run, 2026-11-21).
$ErrorActionPreference = 'Continue'
# Nhat ky theo thang: once its first line is from an earlier month the log moves to scheduler-YYYY-MM.log (six months kept); the new one
# carries the last 200 lines, so Tinh trang he thong still finds the last finished run.
$rotated = & $python -W ignore -m investment_agent.jobs.log_rotate $log 2>$null
"$(Get-Date -Format o) log-rotate exit=$LASTEXITCODE $rotated" | Add-Content -LiteralPath $log -Encoding UTF8
$data = Join-Path $script:RepoRoot 'data'
New-Item -ItemType Directory -Force -Path $data | Out-Null
$calendar = Join-Path $data 'trading-calendar.json'
if (-not (Test-Path -LiteralPath $calendar)) { $calendar = Join-Path $script:RepoRoot "config\trading-calendar-hose-$((Get-Date).Year).json" }
$symbols = Join-Path $data 'market-symbols.txt'
# Index constituents and sectors change a few times a year; refresh the VN30/VN100 labels and ICB sectors weekly.
$weekAgo = (Get-Date).AddDays(-7)
$groups = Join-Path $data 'index-groups.json'
if ((Test-Path -LiteralPath $symbols) -and (-not (Test-Path -LiteralPath $groups) -or (Get-Item -LiteralPath $groups).LastWriteTime -lt $weekAgo)) {
    $refresh = & $python -W ignore -m investment_agent.jobs.step index-groups --output $groups 2>$null
    "$(Get-Date -Format o) index-groups exit=$LASTEXITCODE $refresh" | Add-Content -LiteralPath $log -Encoding UTF8
}
$sectors = Join-Path $data 'industries.json'
if ((Test-Path -LiteralPath $symbols) -and (-not (Test-Path -LiteralPath $sectors) -or (Get-Item -LiteralPath $sectors).LastWriteTime -lt $weekAgo)) {
    $refresh = & $python -W ignore -m investment_agent.jobs.step industries --symbols "@$symbols" --output $sectors 2>$null
    "$(Get-Date -Format o) industries exit=$LASTEXITCODE $refresh" | Add-Content -LiteralPath $log -Encoding UTF8
}
if (Test-Path -LiteralPath $symbols) {
    $sync = & $python -W ignore -m investment_agent.jobs.step --timeout 900 market-sync --symbols "@$symbols" --data-dir $data --calendar $calendar --days 10 2>$null
    "$(Get-Date -Format o) market-sync exit=$LASTEXITCODE $sync" | Add-Content -LiteralPath $log -Encoding UTF8
    $sync = & $python -W ignore -m investment_agent.jobs.step --timeout 900 market-sync --symbols VNINDEX --index --data-dir $data --calendar $calendar --days 10 2>$null
    "$(Get-Date -Format o) market-sync VNINDEX exit=$LASTEXITCODE $sync" | Add-Content -LiteralPath $log -Encoding UTF8
}
# Public macro feeds (FRED, Vietcombank); a failing source is logged and the run continues.
$macro = & $python -W ignore -m investment_agent.jobs.step macro-sync --data-dir $data 2>$null
"$(Get-Date -Format o) macro-sync exit=$LASTEXITCODE $macro" | Add-Content -LiteralPath $log -Encoding UTF8
# Nhac vi mo: Den tin hieu rui ro vi mo and Nhac thanh khoan va ty gia in one Telegram note (owner, 21/11/2026).
$ma = & $python -W ignore -m investment_agent.jobs.step macro-alerts --data-dir $data 2>$null
"$(Get-Date -Format o) macro-alerts exit=$LASTEXITCODE $ma" | Add-Content -LiteralPath $log -Encoding UTF8
# Nhac loi nguon: one Telegram note when a public source failed three runs in a row, and one when it is back.
$sa = & $python -W ignore -m investment_agent.jobs.step source-alerts --data-dir $data 2>$null
"$(Get-Date -Format o) source-alerts exit=$LASTEXITCODE $sa" | Add-Content -LiteralPath $log -Encoding UTF8
# Nhac chenh lech vang SJC: one Telegram note when the gap to the world price crosses the owner's threshold, and when it is back under.
$sg = & $python -W ignore -m investment_agent.jobs.step sjc-gap-alerts --data-dir $data 2>$null
"$(Get-Date -Format o) sjc-gap-alerts exit=$LASTEXITCODE $sg" | Add-Content -LiteralPath $log -Encoding UTF8
# Lich vi mo My: the Fed's and BLS's calendars read once a day, one Telegram note an event the day before (Vietnam time).
$uc = & $python -W ignore -m investment_agent.jobs.step us-calendar --data-dir $data 2>$null
"$(Get-Date -Format o) us-calendar exit=$LASTEXITCODE $uc" | Add-Content -LiteralPath $log -Encoding UTF8
# Do lich HOSE: from 1 December while next year's trading calendar file is missing, one Telegram note when HOSE posts its holiday notice.
$cw = & $python -W ignore -m investment_agent.jobs.step calendar-watch --data-dir $data 2>$null
"$(Get-Date -Format o) calendar-watch exit=$LASTEXITCODE $cw" | Add-Content -LiteralPath $log -Encoding UTF8
# Dinh gia chi so: daily P/E and P/B of VNINDEX and VN30 from VNDirect's public API (whole history once, then the last 14 days).
$ivs = & $python -W ignore -m investment_agent.jobs.step index-valuation-sync --data-dir $data 2>$null
"$(Get-Date -Format o) index-valuation-sync exit=$LASTEXITCODE $ivs" | Add-Content -LiteralPath $log -Encoding UTF8
# Chat luong bao cao: quarterly ratios of watched banks, securities firms and insurers (VNDirect public API), one call each.
$frs = & $python -W ignore -m investment_agent.jobs.step financial-ratios-sync --data-dir $data 2>$null
"$(Get-Date -Format o) financial-ratios-sync exit=$LASTEXITCODE $frs" | Add-Content -LiteralPath $log -Encoding UTF8
# Chung chi quy theo NAV: every open-ended fund's NAV from Fmarket (one public call, names no fund).
$fn = & $python -W ignore -m investment_agent.jobs.step fund-nav-sync --data-dir $data 2>$null
"$(Get-Date -Format o) fund-nav-sync exit=$LASTEXITCODE $fn" | Add-Content -LiteralPath $log -Encoding UTF8
# Chi bao luan diem: one Telegram note for thesis indicators newly at their bad level and scenario reviews due.
$tl = & $python -W ignore -m investment_agent.jobs.step thesis-lights --data-dir $data 2>$null
"$(Get-Date -Format o) thesis-lights exit=$LASTEXITCODE $tl" | Add-Content -LiteralPath $log -Encoding UTF8
# Lich vi mo: one Telegram note the day before the owner's events marked for a reminder (sent once per event).
$me = & $python -W ignore -m investment_agent.jobs.step macro-events-remind --data-dir $data 2>$null
"$(Get-Date -Format o) macro-events-remind exit=$LASTEXITCODE $me" | Add-Content -LiteralPath $log -Encoding UTF8
# Danh muc cua quy: every fund's published top holdings (Fmarket); a fund is read again only when its month changes.
$fh = & $python -W ignore -m investment_agent.jobs.step fund-holdings-sync --data-dir $data 2>$null
"$(Get-Date -Format o) fund-holdings-sync exit=$LASTEXITCODE $fh" | Add-Content -LiteralPath $log -Encoding UTF8
# Vang theo gia Phu Quy: every kind's buying and selling price per chi from Phu Quy's home page (one public page).
$gp = & $python -W ignore -m investment_agent.jobs.step gold-price-sync --data-dir $data 2>$null
"$(Get-Date -Format o) gold-price-sync exit=$LASTEXITCODE $gp" | Add-Content -LiteralPath $log -Encoding UTF8
# CAPM hint: beta of every watched ticker (VNDirect public API), one call.
$bs = & $python -W ignore -m investment_agent.jobs.step beta-sync --data-dir $data 2>$null
"$(Get-Date -Format o) beta-sync exit=$LASTEXITCODE $bs" | Add-Content -LiteralPath $log -Encoding UTF8
# CAPM default ERP: Damodaran (NYU Stern) for Vietnam, read at most weekly.
$es = & $python -W ignore -m investment_agent.jobs.step erp-sync --data-dir $data 2>$null
"$(Get-Date -Format o) erp-sync exit=$LASTEXITCODE $es" | Add-Content -LiteralPath $log -Encoding UTF8
# Ban tin tuan: weekend runs only, once per week (only when scheduled delivery is on).
$wb = & $python -W ignore -m investment_agent.jobs.step weekly-brief --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) weekly-brief exit=$LASTEXITCODE $wb" | Add-Content -LiteralPath $log -Encoding UTF8
# Public research reports (ACBS, World Bank): AI reads public report text only; at most 3 new reports, once per 6 hours.
$ins = & $python -W ignore -m investment_agent.jobs.step insights-run --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) insights-run exit=$LASTEXITCODE $ins" | Add-Content -LiteralPath $log -Encoding UTF8
# Xu hướng board (MACD/RSI over M, W, D1, H4, H1) from 15:30 on trading days; skips itself otherwise.
$trend = & $python -W ignore -m investment_agent.jobs.step trend-run --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) trend-run exit=$LASTEXITCODE $trend" | Add-Content -LiteralPath $log -Encoding UTF8
# Public market snapshot of the latest session for the brief (whole-HOSE board, indices, HOSE statistics, news RSS).
$brief = & $python -W ignore -m investment_agent.jobs.step brief-snapshot --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) brief-snapshot exit=$LASTEXITCODE $brief" | Add-Content -LiteralPath $log -Encoding UTF8
# Nhac chuoi tin hieu: one Telegram note when thin trading, a green index over falling stocks or VN-Index against Asia has run for days.
$sr = & $python -W ignore -m investment_agent.jobs.step signal-runs-alerts --data-dir $data 2>$null
"$(Get-Date -Format o) signal-runs-alerts exit=$LASTEXITCODE $sr" | Add-Content -LiteralPath $log -Encoding UTF8
# Corporate events of watched tickers (dividends, issues, shareholder meetings): refreshed daily, reminder 5 days ahead.
$events = & $python -W ignore -m investment_agent.jobs.step events-sync --data-dir $data 2>$null
"$(Get-Date -Format o) events-sync exit=$LASTEXITCODE $events" | Add-Content -LiteralPath $log -Encoding UTF8
# Nhat ky: remind what was written when a journalled ticker moved another 15% (threshold in Cai dat).
$journal = & $python -W ignore -m investment_agent.jobs.step journal-review --data-dir $data 2>$null
"$(Get-Date -Format o) journal-review exit=$LASTEXITCODE $journal" | Add-Content -LiteralPath $log -Encoding UTF8
# Viec tai chinh hom nay: so tiet kiem dao han, het lai uu dai, bao hiem, cho thue, Thap tai san, gop von deu and ke hoach tich san
# in one Telegram note (after prices, NAVs and gold are synced; only when scheduled delivery is on). Each keeps its own rule.
$wa = & $python -W ignore -m investment_agent.jobs.step wealth-alerts --data-dir $data 2>$null
"$(Get-Date -Format o) wealth-alerts exit=$LASTEXITCODE $wa" | Add-Content -LiteralPath $log -Encoding UTF8
# Statements for the Định giá page: from the 20:00 slot, refresh the 8 stalest tickers (about 3 minutes, paced for Vnstock's limit).
if ((Get-Date).Hour -ge 20) {
    $fund = & $python -W ignore -m investment_agent.jobs.step fundamentals-sync --data-dir $data --limit 8 2>$null
    "$(Get-Date -Format o) fundamentals-sync exit=$LASTEXITCODE $fund" | Add-Content -LiteralPath $log -Encoding UTF8
    # Bao cao quy moi: Telegram note for tickers whose new quarter the sync just found (only when scheduled delivery is on).
    $qa = & $python -W ignore -m investment_agent.jobs.step quarter-alerts --data-dir $data 2>$null
    "$(Get-Date -Format o) quarter-alerts exit=$LASTEXITCODE $qa" | Add-Content -LiteralPath $log -Encoding UTF8
    # Bang so tai chinh: full statements of the 8 stalest watched non-financial tickers (VNDirect public API, two calls each).
    $ss = & $python -W ignore -m investment_agent.jobs.step statements-sync --data-dir $data --limit 8 2>$null
    "$(Get-Date -Format o) statements-sync exit=$LASTEXITCODE $ss" | Add-Content -LiteralPath $log -Encoding UTF8
    # Nhac dau hieu phai thu moi: one Telegram note when a held ticker shows a receivable sign it did not show before.
    $ra = & $python -W ignore -m investment_agent.jobs.step receivable-alerts --data-dir $data 2>$null
    "$(Get-Date -Format o) receivable-alerts exit=$LASTEXITCODE $ra" | Add-Content -LiteralPath $log -Encoding UTF8
    # Gia dai han da dieu chinh: VNDirect's adjusted daily closes since 2013 for 60 HOSE tickers a night (every listed one within a week).
    $ph = & $python -W ignore -m investment_agent.jobs.step price-history-sync --data-dir $data --limit 60 2>$null
    "$(Get-Date -Format o) price-history-sync exit=$LASTEXITCODE $ph" | Add-Content -LiteralPath $log -Encoding UTF8
    # Tu doanh theo phien: HOSE proprietary trading of each session VNDirect has posted, about a year kept (one call a session), for tu_doanh.
    $pt = & $python -W ignore -m investment_agent.jobs.step proprietary-sync --data-dir $data --limit 260 2>$null
    "$(Get-Date -Format o) proprietary-sync exit=$LASTEXITCODE $pt" | Add-Content -LiteralPath $log -Encoding UTF8
    # Lich su dinh gia cua ma: statements and unadjusted closes of 60 HOSE tickers a night (all within a week), so dinh_gia_lich_su and
    # the P/E, P/B so voi lich su cards on Bang so tai chinh stay current.
    $ih = & $python -W ignore -m investment_agent.jobs.step index-history-sync --data-dir $data --limit 60 2>$null
    "$(Get-Date -Format o) index-history-sync exit=$LASTEXITCODE $ih" | Add-Content -LiteralPath $log -Encoding UTF8
    # Chi so tai chinh doanh nghiep thuong: VNDirect's quarterly ratios for 60 non-financial HOSE tickers a night (all within a week).
    $gr = & $python -W ignore -m investment_agent.jobs.step general-ratios-sync --data-dir $data --limit 60 2>$null
    "$(Get-Date -Format o) general-ratios-sync exit=$LASTEXITCODE $gr" | Add-Content -LiteralPath $log -Encoding UTF8
    # Doi chieu dinh gia: VNDirect's market value, P/E and P/B of watched tickers (one public call each).
    $vc = & $python -W ignore -m investment_agent.jobs.step valuation-check-sync --data-dir $data 2>$null
    "$(Get-Date -Format o) valuation-check-sync exit=$LASTEXITCODE $vc" | Add-Content -LiteralPath $log -Encoding UTF8
    # Thuyet minh ngan hang: loans by group and deposits by kind of watched banks from Vietcap's notes (one call each, 10 s apart,
    # weekly per bank), for the group-2 share and CASA in Chi so ngan hang.
    $bn = & $python -W ignore -m investment_agent.jobs.step bank-notes-sync --data-dir $data 2>$null
    "$(Get-Date -Format o) bank-notes-sync exit=$LASTEXITCODE $bn" | Add-Content -LiteralPath $log -Encoding UTF8
    # Thuyet minh tu dong: borrowings, financial income and costs by kind, fixed-asset movements from Vietcap's notes: watched companies
    # first and weekly, every other non-financial HOSE company every two weeks (after the bank notes: 10 s before each call, at most 40 a run).
    $cn = & $python -W ignore -m investment_agent.jobs.step company-notes-sync --data-dir $data 2>$null
    "$(Get-Date -Format o) company-notes-sync exit=$LASTEXITCODE $cn" | Add-Content -LiteralPath $log -Encoding UTF8
    # So luong tu van ban HOSE: volumes VNDirect lacks, read on this machine (OCR) from the PDFs attached to watched tickers' HOSE
    # result reports, kept only when before +/- traded = after; each notice once, at most 30 a night, 1 s between calls.
    $idoc = & $python -W ignore -m investment_agent.jobs.step --timeout 900 insider-docs-sync --data-dir $data --limit 30 2>$null
    "$(Get-Date -Format o) insider-docs-sync exit=$LASTEXITCODE $idoc" | Add-Content -LiteralPath $log -Encoding UTF8
    # Ke hoach nam: the current year's business plan of each watched ticker from CafeF (one public call each, weekly per ticker).
    $ps = & $python -W ignore -m investment_agent.jobs.step plans-sync --data-dir $data 2>$null
    "$(Get-Date -Format o) plans-sync exit=$LASTEXITCODE $ps" | Add-Content -LiteralPath $log -Encoding UTF8
}
# Bo loc tin hieu: tickers new to the owner's notifying screens (after Xu huong and the session snapshot above).
$sc = & $python -W ignore -m investment_agent.jobs.step screen-check --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) screen-check exit=$LASTEXITCODE $sc" | Add-Content -LiteralPath $log -Encoding UTF8
# Danh muc hom nay: ke hoach giai ngan, giao dich noi bo moi, ke hoach sut giam (full price history once per ticker) and luan diem
# dau tu (every condition on stored data) in one Telegram note, after every source they read. 15 minutes: the history fill is paced.
$pf = & $python -W ignore -m investment_agent.jobs.step --timeout 900 portfolio-alerts --data-dir $data --calendar $calendar 2>$null
"$(Get-Date -Format o) portfolio-alerts exit=$LASTEXITCODE $pf" | Add-Content -LiteralPath $log -Encoding UTF8
$summary = & $python -W ignore -m investment_agent.jobs.step scheduled-run --calendar $calendar --data-dir $data 2>$null
$runExit = $LASTEXITCODE
"$(Get-Date -Format o) exit=$runExit $summary" | Add-Content -LiteralPath $log -Encoding UTF8
# At most one backup per day, after the evening slot (or as a catch-up); retention prunes old ones.
$backup = & $python -W ignore -m investment_agent.jobs.step backup --kind auto --data-dir $data --backup-dir (Join-Path $script:RepoRoot 'backups') 2>$null
"$(Get-Date -Format o) backup exit=$LASTEXITCODE $backup" | Add-Content -LiteralPath $log -Encoding UTF8
# Bang den chi bao som: Telegram when one of the owner's indicators changes colour.
$lc = & $python -W ignore -m investment_agent.jobs.step lights-check --data-dir $data 2>$null
"$(Get-Date -Format o) lights-check exit=$LASTEXITCODE $lc" | Add-Content -LiteralPath $log -Encoding UTF8
# Tinh trang he thong: restore the newest backup into a temporary folder once a week, then say what stopped working.
$drill = & $python -W ignore -m investment_agent.jobs.step backup-drill --data-dir $data 2>$null
"$(Get-Date -Format o) backup-drill exit=$LASTEXITCODE $drill" | Add-Content -LiteralPath $log -Encoding UTF8
$hc = & $python -W ignore -m investment_agent.jobs.step health-check --data-dir $data 2>$null
"$(Get-Date -Format o) health-check exit=$LASTEXITCODE $hc" | Add-Content -LiteralPath $log -Encoding UTF8
"$(Get-Date -Format o) finish exit=$runExit pid=$PID" | Add-Content -LiteralPath $log -Encoding UTF8
exit $runExit
