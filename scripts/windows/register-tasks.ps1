# Show (default) or register (-Register) the scheduled after-close task for the current user.
# Registration refuses to proceed until configuration exists; it touches no other scheduled task.
param([switch]$Register, [switch]$Unregister)
. (Join-Path $PSScriptRoot 'common.ps1')
$name = 'InvestmentAgent-AfterClose'
$script = Join-Path $PSScriptRoot 'run-after-close.ps1'
$argument = "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$times = @('08:30', '15:30', '20:00')

if ($Unregister) {
    if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { Unregister-ScheduledTask -TaskName $name -Confirm:$false }
    Write-Host "Đã gỡ $name (nếu có)."
    return
}

Write-Host "Tác vụ: $name"
Write-Host "Lệnh: powershell.exe $argument"
Write-Host "Kích hoạt: hằng ngày lúc $($times -join ', ') (giờ máy, cần đặt múi giờ Asia/Ho_Chi_Minh) và khi đăng nhập (chạy bù)."
if (-not $Register) { Write-Host 'Chưa đăng ký. Chạy lại với -Register sau khi cấu hình xong.'; return }

$calendars = @('data\trading-calendar.json', "config\trading-calendar-hose-$((Get-Date).Year).json")
$missing = @('.env.local') | Where-Object { -not (Test-Path -LiteralPath (Join-Path $script:RepoRoot $_)) }
if (-not ($calendars | Where-Object { Test-Path -LiteralPath (Join-Path $script:RepoRoot $_) })) { $missing += 'lịch giao dịch năm nay' }
if ($missing) { throw "Chưa đủ cấu hình: $($missing -join ', ')" }
if ((Get-TimeZone).Id -ne 'SE Asia Standard Time') { throw 'Múi giờ máy không phải UTC+07 (SE Asia Standard Time); lịch chạy sẽ lệch.' }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argument -WorkingDirectory $script:RepoRoot
$triggers = @($times | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ }) + @(New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$existing = [bool](Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue)
# -Force replaces our own task of the same name, so running -Register again updates it instead of failing.
Register-ScheduledTask -TaskName $name -Action $action -Trigger $triggers -Settings $settings -Description 'Bản tin sau phiên (chạy bù khi máy bật lại)' `
    -Force -ErrorAction Stop | Out-Null
Write-Host "$(if ($existing) { 'Đã cập nhật' } else { 'Đã đăng ký' }) $name. Máy tắt hoặc ngủ thì không bảo đảm chạy đúng giờ; lần bật sau sẽ chạy bù phiên gần nhất."
