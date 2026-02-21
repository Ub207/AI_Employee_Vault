@echo off
schtasks /Create /TN "PM2_WhatsApp_Watcher" /TR "wscript.exe D:\AI_Employee_Vault\pm2_silent_start.vbs" /SC ONLOGON /RL HIGHEST /F
if %errorlevel% == 0 (
    echo.
    echo SUCCESS! PM2 will auto-start on Windows login.
) else (
    echo.
    echo FAILED - Admin rights chahiye.
)
echo.
pause
