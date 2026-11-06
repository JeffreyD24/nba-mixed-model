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
  for f in state/heartbeat_alert.txt state/alerts.csv state/market_moves.csv state/line_history.csv state/line_jumps.csv state/test_alert_result.txt state/injury_status_seen.csv state/key_player_alerts.csv state/openers_seen.json state/bluesky_seen.json state/news_overrides.json state/poly_paper.csv state/poly_last.json state/pinnacle_now.json state/pinnacle_off state/ml_test.csv state/report_watch_seen.json state/report_watch_last.csv state/bailout_alerts.csv state/dk_direct_now.json state/dk_direct_last.json ncaab/state/dk_lines.csv ncaab/state/live_evals.csv ncaab/state/live_bets.csv ncaab/state/live_paper_v2.csv ncaab/state/live_poll.json ncaab/state/live_stop.txt; do
    if [ -f "$f" ]; then git add "$f"; fi
  done
  if [ -d state/market_models ]; then git add state/market_models; fi
  if [ -d research ]; then git add research; fi
  git diff --cached --quiet && return 0
  git commit -q -m "Alerts $(TZ=America/New_York date '+%F %H:%M')"
  for i in 1 2 3; do
    if git pull --rebase --autostash -q && git push -q; then return 0; fi
    git rebase --abort 2>/dev/null
    sleep 5
  done
  echo "Could not save this check; resetting to the latest saved state."
  git fetch -q && git reset -q --hard origin/main
}

while :; do
  while busy; do echo "Another run is saving; waiting."; sleep 30; done
  git pull --rebase --autostash -q || { git rebase --abort 2>/dev/null; git fetch -q; git reset -q --hard origin/main; }
  echo "=== check at $(TZ=America/New_York date '+%F %H:%M:%S') ET ==="
  if python alert.py .; then date -u +%Y-%m-%dT%H:%M:%SZ > state/heartbeat_alert.txt; else echo "Check failed; trying again next time."; fi
  timeout 120 python ncaab/live_alert.py . || echo "NCAAM line check failed; trying again next time."     # Nov 5, 2026: PROVISIONAL stale-line spreads
  timeout 60 python dk_direct.py . || echo "DraftKings direct feed failed; trying again next time."   # Nov 5, 2026: every NBA/NHL/NFL game line, as DraftKings shows it
  python polymarket.py . || echo "Polymarket check failed; trying again next time."
  python pinnacle_watch.py . || echo "Live odds recorder failed; trying again next time."
  timeout 150 python market_models_live.py . check || echo "Market models check failed; continuing."   # Nov 5, 2026: PROVISIONAL movement bets
  timeout 90 python pregame.py . || echo "Pregame recorder failed; continuing."
  timeout 60 python report_watch.py . || echo "Report watch failed; continuing."
  while busy; do echo "Another run is saving; waiting."; sleep 30; done
  save
  NOW=$(date +%s)
  [ $((NOW - START + 300)) -ge "$LIMIT" ] && break
  # until the next 5-minute mark, look for brand-new DraftKings lines every minute; a new line triggers a full check at once
  TARGET=$((NOW + 300 - NOW % 300 + 20))
  while [ "$(date +%s)" -lt "$TARGET" ]; do
    WAIT=$((TARGET - $(date +%s))); [ "$WAIT" -gt 60 ] && WAIT=60
    [ "$WAIT" -gt 0 ] && sleep "$WAIT"
    [ "$(date +%s)" -ge "$TARGET" ] && break
    python bluesky_watch.py .; RC=$?
    if [ "$RC" -eq 10 ]; then echo "Reporter news on a player decision: checking now."; break; fi
    [ "$RC" -ne 0 ] && echo "Bluesky watch failed; continuing."
    timeout 90 python pregame.py . || echo "Pregame recorder failed; continuing."
    timeout 60 python report_watch.py . || echo "Report watch failed; continuing."   # Nov 4, 2026: TEST, logged only
    timeout 60 python dk_direct.py . || echo "DraftKings direct feed failed; continuing."
    python opener_watch.py .; RC=$?
    if [ "$RC" -eq 10 ]; then echo "New DraftKings line: checking now."; break; fi
  done
done
echo "Loop finished after $(( ($(date +%s) - START) / 60 )) minutes."
