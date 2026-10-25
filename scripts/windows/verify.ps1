# Run every automated check and print one result line per check. Exit 1 when any check fails.
# Synthetic data only; live sources, Telegram and AI are never contacted.
. (Join-Path $PSScriptRoot 'common.ps1')
$python = Get-RepoPython
$web = Join-Path $script:RepoRoot 'apps\web'
$checks = [ordered]@{
    'backend pytest'  = { & $python -m pytest (Join-Path $script:RepoRoot 'backend\tests') -q -p no:warnings }
    'web typecheck'   = { npm.cmd --prefix $web run typecheck }
    'web lint'        = { npm.cmd --prefix $web run lint }
    'web unit tests'  = { npm.cmd --prefix $web run test -- --run }
    'web build'       = { npm.cmd --prefix $web run build }
    'browser e2e'     = { npm.cmd --prefix $web run test:e2e -- --reporter=line }
}
$failed = @()
# Native tools write progress to stderr; judge each check by its exit code only.
$ErrorActionPreference = 'Continue'
Push-Location $script:RepoRoot
try {
    foreach ($name in $checks.Keys) {
        $output = & $checks[$name] 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0) { Write-Host "PASS $name" } else { Write-Host "FAIL $name"; Write-Host ($output -split "`n" | Select-Object -Last 15 | Out-String); $failed += $name }
    }
} finally { Pop-Location }
if ($failed) { Write-Host "Không đạt: $($failed -join ', ')"; exit 1 }
Write-Host 'Tất cả kiểm tra tự động đã đạt (dữ liệu tổng hợp; kiểm chứng live chưa chạy).'
