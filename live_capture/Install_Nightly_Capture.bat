@echo off
rem One-time setup: start the live line capture every day at 6:45 PM automatically.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_nightly_task.ps1"
pause
