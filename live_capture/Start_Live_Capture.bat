@echo off
rem Double-click to capture live NBA lines about every 30 seconds. Close the window to stop.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0live_capture.ps1"
pause
