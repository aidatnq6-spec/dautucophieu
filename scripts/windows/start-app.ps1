# Start the Python API and the built Next.js app on loopback, in hidden windows.
# Requires: .env.local, .venv, and `npm --prefix apps/web run build` done once.
. (Join-Path $PSScriptRoot 'common.ps1')
Import-LocalEnv
$python = Get-RepoPython
if ($env:INVESTMENT_E2E_AUTH) { throw 'INVESTMENT_E2E_AUTH chỉ dùng cho kiểm thử; xóa biến này trước khi chạy ứng dụng.' }
$env:INVESTMENT_DATA_DIR = Join-Path $script:RepoRoot 'data'
New-Item -ItemType Directory -Force -Path $env:INVESTMENT_DATA_DIR, (Join-Path $script:RepoRoot 'logs') | Out-Null

Start-Process -FilePath $python -ArgumentList @('-m', 'investment_agent.api.app') -WorkingDirectory $script:RepoRoot -WindowStyle Hidden
Start-Process -FilePath 'npm.cmd' -ArgumentList @('--prefix', (Join-Path $script:RepoRoot 'apps\web'), 'run', 'start') `
    -WorkingDirectory $script:RepoRoot -WindowStyle Hidden
Write-Host "Đã khởi động. Mở $env:APP_ORIGIN trên máy này (chỉ loopback)."
