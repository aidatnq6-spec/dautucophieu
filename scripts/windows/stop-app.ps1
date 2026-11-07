# Stop the Python API and the Next.js app started by start-app.ps1. The venv launcher's python.exe runs the API in a child process
# that ends with it, so a process already gone is skipped, not reported as a failure.
. (Join-Path $PSScriptRoot 'common.ps1')
$targets = @(Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq 'python.exe' -and $_.CommandLine -match 'investment_agent\.api\.app') -or
    ($_.Name -eq 'node.exe' -and $_.CommandLine -match 'next' -and $_.CommandLine -match '\sstart\b' -and $_.CommandLine -match [regex]::Escape($script:RepoRoot))
})
$stopped = 0
foreach ($p in $targets) {
    if (Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue) {
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; $stopped++ } catch { }  # ended between the check and the stop
    }
}
Write-Host "Đã dừng $stopped tiến trình của ứng dụng."
exit 0
