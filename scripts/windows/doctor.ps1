param([switch]$RequireServices)
$ErrorActionPreference = 'Stop'
$failed = $false
foreach ($tool in @('node', 'npm.cmd', 'python', 'git')) {
    if (Get-Command $tool -ErrorAction SilentlyContinue) {
        Write-Output "OK tool: $tool"
    } else {
        Write-Output "MISSING tool: $tool"
        $failed = $true
    }
}
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
foreach ($path in @('.venv/Scripts/python.exe', 'apps/web/node_modules')) {
    if (Test-Path (Join-Path $root $path)) { Write-Output "OK local dependency: $path" }
    else { Write-Output "MISSING local dependency: $path"; $failed = $true }
}
# Process environment only: never load or print secret values from a file.
if ($RequireServices) {
    foreach ($line in Get-Content (Join-Path $root '.env.example')) {
        if ($line -match '^([A-Z][A-Z0-9_]*)=') {
            $name = $Matches[1]
            if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) {
                Write-Output "MISSING variable: $name"
                $failed = $true
            } else { Write-Output "OK variable: $name" }
        }
    }
} else { Write-Output 'Service checks skipped (use -RequireServices); local scaffold needs no credentials.' }
if ($failed) { exit 1 }
Write-Output 'Local prerequisite checks passed. Service connectivity was not tested.'
exit 0
