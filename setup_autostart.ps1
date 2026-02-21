$action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument 'D:\AI_Employee_Vault\pm2_silent_start.vbs'
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest
Register-ScheduledTask -TaskName 'PM2_WhatsApp_Watcher' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force

Write-Host "SUCCESS! PM2 will auto-start on Windows login." -ForegroundColor Green
Write-Host "Press any key to close..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
