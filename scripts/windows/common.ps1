# Shared helpers: absolute repository paths and .env.local loading without printing values.
$ErrorActionPreference = 'Stop'
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

function Import-LocalEnv {
    $rootFile = Join-Path $script:RepoRoot '.env.local'
    $webFile = Join-Path $script:RepoRoot 'apps\web\.env.local'
    $file = if (Test-Path -LiteralPath $rootFile) { $rootFile } elseif (Test-Path -LiteralPath $webFile) { $webFile } else { $rootFile }
    if (-not (Test-Path -LiteralPath $file)) { throw "Thiếu .env.local ở thư mục gốc hoặc apps\web (tạo từ .env.example; không đưa vào Git)." }
    foreach ($line in Get-Content -LiteralPath $file -Encoding UTF8) {
        if ($line -match '^\s*#' -or $line -notmatch '^\s*([A-Z0-9_]+)\s*=\s*(.*)$') { continue }
        $value = $Matches[2].Trim()
        if ($value.Length -ge 2 -and $value.StartsWith('"') -and $value.EndsWith('"')) { $value = $value.Substring(1, $value.Length - 2) }
        [Environment]::SetEnvironmentVariable($Matches[1], $value, 'Process')
    }
}

# update-app.ps1 writes the commit it built and restarted into .next\deployed-commit. Any other build (verify.ps1, a manual one)
# replaces .next and so drops the marker, and a merge made on this machine moves HEAD past it: either way the running app is not
# HEAD's code and must be rebuilt and restarted (26/11/2026).
function Test-WebDeployed([string]$webDir, [string]$head) {
    $marker = Join-Path $webDir '.next\deployed-commit'
    if (-not (Test-Path -LiteralPath $marker)) { return $false }
    return (Get-Content -LiteralPath $marker -TotalCount 1).Trim() -eq $head
}

function Get-RepoPython {
    $python = Join-Path $script:RepoRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw "Thiếu môi trường Python tại $python (chạy scripts\windows\doctor.ps1)." }
    return $python
}
