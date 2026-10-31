@echo off
rem Removes the nightly live line capture task.
powershell -NoProfile -Command "Unregister-ScheduledTask -TaskName \"NBA live line capture\" -Confirm:$false; Write-Host Removed."
pause
