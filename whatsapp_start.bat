@echo off
echo WhatsApp Watcher - Starting...
cd /d D:\AI_Employee_Vault
call .venv\Scripts\activate.bat
python whatsapp_playwright_watcher.py
pause
