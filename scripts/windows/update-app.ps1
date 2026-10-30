# Keep the running app on the latest origin/main. Task Scheduler calls this every 10 minutes (register-tasks.ps1).
# Runs only when the working tree is on main with no tracked changes, so work in progress on a branch is never touched.
# New commits: fast-forward, install dependencies whose lock files changed, build the web app, restart API and web.
# A failed build returns to the previous commit and rebuilds it, so the app keeps running the last good version.
. (Join-Path $PSScriptRoot 'common.ps1')
$log = Join-Path $script:RepoRoot 'logs\update.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
function Write-Log([string]$message) { "$(Get-Date -Format o) $message" | Add-Content -LiteralPath $log -Encoding UTF8 }
function Invoke-Native([string]$step, [scriptblock]$command) {
    $output = & $command 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { Write-Log "$step exit=$LASTEXITCODE"; throw "$step failed" }
}

Set-Location -LiteralPath $script:RepoRoot
$ErrorActionPreference = 'Continue'  # git writes progress to stderr; exit codes decide
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne 'main') { Write-Log "skip branch=$branch"; return }
if (git status --porcelain --untracked-files=no) { Write-Log 'skip tracked-changes'; return }
git fetch --quiet origin main 2>$null
if ($LASTEXITCODE -ne 0) { Write-Log "fetch exit=$LASTEXITCODE"; return }
$old, $new = (git rev-parse HEAD).Trim(), (git rev-parse origin/main).Trim()
if ($old -eq $new) { return }  # nothing new: no log line every 10 minutes
git merge-base --is-ancestor HEAD origin/main
if ($LASTEXITCODE -ne 0) { Write-Log "skip diverged head=$($old.Substring(0, 7))"; return }

$changed = @(git diff --name-only $old $new)
$python = Get-RepoPython
$web = Join-Path $script:RepoRoot 'apps\web'
try {
    Invoke-Native 'merge' { git merge --quiet --ff-only origin/main }
    if ($changed -contains 'backend/requirements.lock') { Invoke-Native 'pip-lock' { & $python -m pip install --quiet -r backend/requirements.lock } }
    if ($changed -contains 'backend/pyproject.toml') { Invoke-Native 'pip-editable' { & $python -m pip install --quiet --no-deps --no-build-isolation -e backend } }
    if ($changed -contains 'apps/web/package-lock.json') { Invoke-Native 'npm-ci' { npm.cmd --prefix $web ci } }
    Invoke-Native 'build' { npm.cmd --prefix $web run build }
    $result = "updated $($old.Substring(0, 7))..$($new.Substring(0, 7))"
} catch {
    Write-Log "failed $($_.Exception.Message); back to $($old.Substring(0, 7))"
    git reset --quiet --hard $old
    try { Invoke-Native 'rebuild-previous' { npm.cmd --prefix $web run build } } catch { Write-Log 'previous build failed too' }
    $result = "kept $($old.Substring(0, 7))"
}
git checkout --quiet -- apps/web/next-env.d.ts 2>$null  # the build rewrites it; never committed

# Restart: stop this repository's API and web processes, then start them again with start-app.ps1.
$repo = [regex]::Escape($script:RepoRoot)
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and ($_.CommandLine -match 'investment_agent\.api\.app' -or ($_.CommandLine -match "$repo\\apps\\web" -and $_.CommandLine -match 'next.*start'))
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'start-app.ps1') | Out-Null
Write-Log "$result restart exit=$LASTEXITCODE"
