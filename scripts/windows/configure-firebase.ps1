# Fill .env.local for Firebase without printing any secret.
#   -ServiceAccountJson  key file downloaded from Firebase Console (keep it OUTSIDE the repository)
#   -WebApiKey           apiKey from the web app config (public by design, still kept local)
#   -OwnerUid            your UID from Authentication > Users (after the first sign-in attempt)
# Existing values are kept unless a new one is given; internal secrets are generated once.
param([string]$ServiceAccountJson, [string]$WebApiKey, [string]$OwnerUid, [string]$EnvFile)
. (Join-Path $PSScriptRoot 'common.ps1')
if (-not $EnvFile) { $EnvFile = Join-Path $script:RepoRoot '.env.local' }

$values = [ordered]@{}
if (Test-Path -LiteralPath $EnvFile) {
    foreach ($line in Get-Content -LiteralPath $EnvFile -Encoding UTF8) {
        if ($line -match '^\s*([A-Z0-9_]+)\s*=(.*)$') { $values[$Matches[1]] = $Matches[2] }
    }
}
function Set-Value($name, $value) { $values[$name] = $value; Write-Host "  da dat $name" }
function New-Secret { $bytes = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes); ($bytes | ForEach-Object { $_.ToString('x2') }) -join '' }

if ($ServiceAccountJson) {
    $resolved = (Resolve-Path -LiteralPath $ServiceAccountJson).Path
    if ($resolved.StartsWith($script:RepoRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Hay de file khoa service account ngoai thu muc du an.' }
    $sa = Get-Content -LiteralPath $resolved -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($sa.type -ne 'service_account' -or -not $sa.private_key -or -not $sa.client_email) { throw 'File khong phai khoa service account hop le.' }
    Set-Value 'FIREBASE_PROJECT_ID' $sa.project_id
    Set-Value 'FIREBASE_CLIENT_EMAIL' $sa.client_email
    Set-Value 'FIREBASE_PRIVATE_KEY' ('"' + ($sa.private_key -replace "`r?`n", '\n') + '"')
    Set-Value 'NEXT_PUBLIC_FIREBASE_PROJECT_ID' $sa.project_id
    Set-Value 'NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN' "$($sa.project_id).firebaseapp.com"
}
if ($WebApiKey) { Set-Value 'NEXT_PUBLIC_FIREBASE_API_KEY' $WebApiKey }
if ($OwnerUid) {
    if ($OwnerUid -notmatch '^[A-Za-z0-9]{10,128}$') { throw 'UID khong hop le.' }
    Set-Value 'FIREBASE_OWNER_UID' $OwnerUid
}
foreach ($name in 'INTERNAL_API_TOKEN', 'INTERNAL_API_HMAC_SECRET') { if (-not $values[$name]) { Set-Value $name (New-Secret) } }
if (-not $values['APP_ORIGIN']) { Set-Value 'APP_ORIGIN' 'http://127.0.0.1:3000' }
if (-not $values['PYTHON_API_ORIGIN']) { Set-Value 'PYTHON_API_ORIGIN' 'http://127.0.0.1:8000' }

$lines = foreach ($k in $values.Keys) { "$k=$($values[$k])" }
[IO.File]::WriteAllLines($EnvFile, [string[]]$lines, (New-Object Text.UTF8Encoding($false)))
$missing = @('FIREBASE_PROJECT_ID', 'FIREBASE_CLIENT_EMAIL', 'FIREBASE_PRIVATE_KEY', 'FIREBASE_OWNER_UID', 'NEXT_PUBLIC_FIREBASE_API_KEY') | Where-Object { -not $values[$_] }
Write-Host "Da ghi $EnvFile (Git bo qua file nay)."
if ($missing) { Write-Host "Con thieu: $($missing -join ', ')" } else { Write-Host 'Du cau hinh Firebase.' }
