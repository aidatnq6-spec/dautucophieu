param([switch]$RequireServices)
$ErrorActionPreference = 'Stop'
$failed = $false
function Test-Runtime($name, $command, $pattern, $supported, $require64Bit = $false) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        Write-Host "MISSING tool: $name"
        return $false
    }
    try {
        $versionText = (& $command --version 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or $versionText -notmatch $pattern) {
            Write-Host "UNSUPPORTED tool: $name (unreadable version; requires $supported)"
            return $false
        }
        $version = [version]$Matches[1]
        $ok = switch ($name) {
            'node' { $version -ge [version]'22.12' -and $version -lt [version]'27.0' }
            'npm.cmd' { $version.Major -eq 11 }
            'python' { $version.Major -eq 3 -and $version.Minor -eq 11 }
            'venv python' { $version.Major -eq 3 -and $version.Minor -eq 11 }
            'git' { $version.Major -eq 2 }
        }
        if ($ok -and $require64Bit) {
            $bits = (& $command -c 'import struct; print(struct.calcsize(chr(80)) * 8)' 2>&1 | Out-String).Trim()
            $ok = $LASTEXITCODE -eq 0 -and $bits -eq '64'
        }
        if (-not $ok) {
            Write-Host "UNSUPPORTED tool: $name ($versionText; requires $supported)"
            return $false
        }
        Write-Host "OK tool: $name ($versionText)"
        if ($name -eq 'node' -and $version.Major -ne 24) {
            Write-Host "WARN tool: node (Node 24 LTS recommended; found $version)"
        }
        return $true
    } catch {
        Write-Host "UNSUPPORTED tool: $name (version probe failed; requires $supported)"
        return $false
    }
}
$checks = @(
    @{ Name = 'node'; Command = 'node'; Pattern = '^v(\d+\.\d+\.\d+)'; Supported = '>=22.12 <27, Node 24 LTS recommended' },
    @{ Name = 'npm.cmd'; Command = 'npm.cmd'; Pattern = '^(\d+\.\d+\.\d+)'; Supported = 'npm 11' },
    @{ Name = 'python'; Command = 'python'; Pattern = '^Python (\d+\.\d+\.\d+)'; Supported = '64-bit Python 3.11'; Require64Bit = $true },
    @{ Name = 'git'; Command = 'git'; Pattern = '^git version (\d+\.\d+\.\d+)'; Supported = 'Git 2' }
)
foreach ($check in $checks) {
    if (-not (Test-Runtime @check)) { $failed = $true }
}
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$venvPython = Join-Path $root '.venv/Scripts/python.exe'
if (Test-Path $venvPython) {
    if (-not (Test-Runtime 'venv python' $venvPython '^Python (\d+\.\d+\.\d+)' '64-bit Python 3.11' $true)) {
        $failed = $true
    }
} else {
    Write-Output 'MISSING local dependency: .venv/Scripts/python.exe'
    $failed = $true
}
if (Test-Path (Join-Path $root 'apps/web/node_modules')) {
    Write-Output 'OK local dependency: apps/web/node_modules'
} else {
    Write-Output 'MISSING local dependency: apps/web/node_modules'
    $failed = $true
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
