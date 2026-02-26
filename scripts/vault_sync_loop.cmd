@echo off
REM Vault Sync Loop — Platinum Tier (Windows CMD wrapper for PM2)
REM Delegates to the PS1 which has its own while-loop + Start-Sleep.
REM PM2 autorestart handles crash recovery.

powershell -ExecutionPolicy Bypass -File "%~dp0vault_sync_loop.ps1"
