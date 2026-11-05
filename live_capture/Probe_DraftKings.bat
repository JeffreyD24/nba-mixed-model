@echo off
REM One-time check: can this computer read DraftKings' own Connecticut odds feed? Double-click, then send Claude a screenshot.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dk_probe.ps1"
pause
