@echo off
echo WhatsApp Watcher - Setup Mode
echo ==============================
cd /d D:\AI_Employee_Vault
call .venv\Scripts\activate.bat
python whatsapp_playwright_watcher.py --setup
pause
