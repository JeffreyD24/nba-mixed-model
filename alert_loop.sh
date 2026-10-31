#!/usr/bin/env bash
# Runs the line check every 5 minutes for about 50 minutes, saving after each check.
# GitHub's scheduler often starts "every 5 minutes" jobs 30-60 minutes apart, so each run keeps itself going
# instead. A new run queues behind this one, so the checks continue without overlapping.
# Waits while a morning, evening or bet-logging run is in progress so their saves don't collide.
set -u
git config user.name "nba-tracker-bot"
git config user.email "actions@users.noreply.github.com"
START=$(date +%s)
LIMIT=${LOOP_SECONDS:-3000}

busy() {   # 0 if another state-writing workflow is running
  for wf in morning.yml evening.yml log-bet.yml; do
    n=$(gh run list --workflow "$wf" --status in_progress --json databaseId --jq length 2>/dev/null || echo 0)
    q=$(gh run list --workflow "$wf" --status queued --json databaseId --jq length 2>/dev/null || echo 0)
    if [ "${n:-0}" != "0" ] || [ "${q:-0}" != "0" ]; then return 0; fi
  done
  return 1
}

save() {
  for f in state/alerts.csv state/market_moves.csv state/line_history.csv state/line_jumps.csv state/test_alert_result.txt state/injury_status_seen.csv state/key_player_alerts.csv; do
    if [ -f "$f" ]; then git add "$f"; fi
  done
  if [ -d research ]; then git add research; fi
  git diff --cached --quiet && return 0
  git commit -q -m "Alerts $(TZ=America/New_York date '+%F %H:%M')"
  for i in 1 2 3; do
    if git pull --rebase -q && git push -q; then return 0; fi
    git rebase --abort 2>/dev/null
    sleep 5
  done
  echo "Could not save this check; resetting to the latest saved state."
  git fetch -q && git reset -q --hard origin/main
}

while :; do
  while busy; do echo "Another run is saving; waiting."; sleep 30; done
  git pull --rebase -q || { git rebase --abort 2>/dev/null; git fetch -q; git reset -q --hard origin/main; }
  echo "=== check at $(TZ=America/New_York date '+%F %H:%M:%S') ET ==="
  python alert.py . || echo "Check failed; trying again next time."
  while busy; do echo "Another run is saving; waiting."; sleep 30; done
  save
  NOW=$(date +%s)
  [ $((NOW - START + 300)) -ge "$LIMIT" ] && break
  sleep $((300 - NOW % 300 + 20))   # next 5-minute mark (+20s)
done
echo "Loop finished after $(( ($(date +%s) - START) / 60 )) minutes."
