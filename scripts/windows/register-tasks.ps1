# Show (default) or register (-Register) the scheduled tasks for the current user: the after-close run and the
# app auto-update (latest origin/main every 10 minutes, see update-app.ps1).
# Registration refuses to proceed until configuration exists; it touches no other scheduled task.
param([switch]$Register, [switch]$Unregister)
. (Join-Path $PSScriptRoot 'common.ps1')
$name = 'InvestmentAgent-AfterClose'
$script = Join-Path $PSScriptRoot 'run-after-close.ps1'
$argument = "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$times = @('08:30', '15:30', '20:00')
$updateName = 'InvestmentAgent-Update'
$updateArgument = "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$(Join-Path $PSScriptRoot 'update-app.ps1')`""

if ($Unregister) {
    foreach ($n in $name, $updateName) {
        if (Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue) { Unregister-ScheduledTask -TaskName $n -Confirm:$false }
    }
    Write-Host "Đã gỡ $name và $updateName (nếu có)."
    return
}

Write-Host "Tác vụ: $name"
Write-Host "Lệnh: powershell.exe $argument"
Write-Host "Kích hoạt: hằng ngày lúc $($times -join ', ') (giờ máy, cần đặt múi giờ Asia/Ho_Chi_Minh) và khi đăng nhập (chạy bù)."
Write-Host "Tác vụ: $updateName — 10 phút một lần và khi đăng nhập: khi main trên GitHub có bản mới thì kéo về, build và khởi động lại ứng dụng (chỉ khi thư mục đang ở main, không có thay đổi chưa commit)."
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

$updateAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $updateArgument -WorkingDirectory $script:RepoRoot
$updateTriggers = @((New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 10)),
    (New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME))
$updateSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
Register-ScheduledTask -TaskName $updateName -Action $updateAction -Trigger $updateTriggers -Settings $updateSettings `
    -Description 'Chạy bản mới nhất của main (kéo về, build, khởi động lại)' -Force -ErrorAction Stop | Out-Null
Write-Host "Đã đăng ký $updateName. Nhật ký: logs\update.log."
