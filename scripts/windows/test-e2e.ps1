param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PlaywrightArgs)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$web = Join-Path $repo 'apps\web'
$python = Join-Path $repo '.venv\Scripts\python.exe'
$playwright = Join-Path $web 'node_modules\.bin\playwright.cmd'
if (-not (Test-Path -LiteralPath $python)) { throw "Missing $python" }
if (-not (Test-Path -LiteralPath $playwright)) { throw "Missing Playwright; run npm ci in apps/web." }

$env:FIREBASE_OWNER_UID = 'e2e-owner'
$env:INTERNAL_API_TOKEN = [guid]::NewGuid().ToString('N')
$env:INTERNAL_API_HMAC_SECRET = [guid]::NewGuid().ToString('N')
$env:APP_ORIGIN = 'http://127.0.0.1:3100'
$env:PYTHON_API_ORIGIN = 'http://127.0.0.1:8765'
$env:E2E_PYTHON_PORT = '8765'
$env:INVESTMENT_E2E_AUTH = '1'
$env:INVESTMENT_E2E_SESSION = [guid]::NewGuid().ToString('N')
$env:E2E_EXTERNAL_SERVERS = '1'

$backend = $null
$frontend = $null
function Wait-Url([string]$Url, [int]$Seconds) {
    $end = (Get-Date).AddSeconds($Seconds)
    do {
        try { Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2 | Out-Null; return } catch { Start-Sleep -Milliseconds 250 }
    } while ((Get-Date) -lt $end)
    throw "E2E server did not become ready: $Url"
}
function Stop-E2eListeners {
    $ids = netstat.exe -ano -p tcp | Select-String ':3100\s|:8765\s' | ForEach-Object {
        $columns = ($_ -split '\s+') | Where-Object { $_ }
        if ($columns.Count -ge 5 -and $columns[3] -eq 'LISTENING') { $columns[4] }
    } | Sort-Object -Unique
    foreach ($idValue in $ids) {
        if ($idValue -match '^\d+$' -and $idValue -ne '0') {
            Stop-Process -Id ([int]$idValue) -Force -ErrorAction SilentlyContinue
        }
    }
}

$occupied = netstat.exe -ano -p tcp | Select-String 'LISTENING' | Select-String ':3100\s|:8765\s'
if ($occupied) { throw 'E2E port 3100 or 8765 is already in use; stop the old test run first.' }

try {
    $backend = Start-Process -FilePath $python -ArgumentList @((Join-Path $repo 'tests\e2e\fixture_backend.py')) -WorkingDirectory $repo -WindowStyle Hidden -PassThru
    $frontend = Start-Process -FilePath 'node.exe' -ArgumentList @('node_modules/next/dist/bin/next', 'dev', '--hostname', '127.0.0.1', '--port', '3100') `
        -WorkingDirectory $web -WindowStyle Hidden -PassThru
    Wait-Url 'http://127.0.0.1:8765/health' 60
    Wait-Url 'http://127.0.0.1:3100/login' 180
    & $playwright test @PlaywrightArgs
    exit $LASTEXITCODE
} finally {
    Stop-E2eListeners
}
