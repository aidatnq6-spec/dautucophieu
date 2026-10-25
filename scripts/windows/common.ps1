# Shared helpers: absolute repository paths and .env.local loading without printing values.
$ErrorActionPreference = 'Stop'
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

function Import-LocalEnv {
    $file = Join-Path $script:RepoRoot '.env.local'
    if (-not (Test-Path -LiteralPath $file)) { throw "Thiếu $file (tạo từ .env.example; không đưa vào Git)." }
    foreach ($line in Get-Content -LiteralPath $file -Encoding UTF8) {
        if ($line -match '^\s*#' -or $line -notmatch '^\s*([A-Z0-9_]+)\s*=\s*(.*)$') { continue }
        $value = $Matches[2].Trim()
        if ($value.Length -ge 2 -and $value.StartsWith('"') -and $value.EndsWith('"')) { $value = $value.Substring(1, $value.Length - 2) }
        [Environment]::SetEnvironmentVariable($Matches[1], $value, 'Process')
    }
}

function Get-RepoPython {
    $python = Join-Path $script:RepoRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw "Thiếu môi trường Python tại $python (chạy scripts\windows\doctor.ps1)." }
    return $python
}
