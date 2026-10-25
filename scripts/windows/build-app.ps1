# Build the web app with .env.local loaded, so NEXT_PUBLIC_* values are embedded at build time.
. (Join-Path $PSScriptRoot 'common.ps1')
Import-LocalEnv
foreach ($name in 'NEXT_PUBLIC_FIREBASE_API_KEY', 'NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN', 'NEXT_PUBLIC_FIREBASE_PROJECT_ID') {
    if (-not [Environment]::GetEnvironmentVariable($name)) { throw "Thieu $name trong .env.local (chay configure-firebase.ps1)." }
}
npm.cmd --prefix (Join-Path $script:RepoRoot 'apps\web') run build
exit $LASTEXITCODE
