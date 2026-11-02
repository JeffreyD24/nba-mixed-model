@echo off
rem One-time: download past seasons of NBA tracking stats (several hours; leave the laptop on and plugged in).
rem Safe to stop and start again: it skips everything already downloaded.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nba_tracking.ps1" -Backfill
pause
