# One-time setup: start the live line capture automatically at 6:45 PM on weekdays and 12:15 PM on weekends (afternoon
# games), waking the computer if it's asleep. Running it again replaces the old schedule.
# Run by double-clicking Install_Nightly_Capture.bat. To remove it later: Remove_Nightly_Capture.bat.
$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "live_capture.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$script`"" -WorkingDirectory $PSScriptRoot
$trigger = @(
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 6:45PM),
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday, Sunday -At 12:15PM))
$settings = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 16) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "NBA live line capture" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Records live NBA lines every 30 seconds during games (My Mixed Model with Claude)." -Force | Out-Null
Write-Host ""
Write-Host "Done. The live line capture will start by itself at 6:45 PM on weekdays and 12:15 PM on weekends, and stop when the night's games are final."
Write-Host "It wakes the computer if it's asleep (Windows needs 'Allow wake timers' on, which is the default when plugged in)."
Write-Host "Keep the laptop plugged in on game nights. Closing the lid can still put it to sleep: see README.md."
