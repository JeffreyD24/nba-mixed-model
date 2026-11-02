@echo off
rem Download today's NBA tracking and hustle stats now (also runs by itself every morning once installed).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nba_tracking.ps1"
pause
