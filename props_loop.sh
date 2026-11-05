#!/usr/bin/env bash
# Nov 5, 2026: FanDuel prop lines + PROVISIONAL prop alerts every ~2 minutes for ~50 minutes (Jeffrey: alerts as fast as possible
# after a line posts). A new run queues behind this one (props-loop.yml, every 10 minutes), so checks continue without gaps.
set -u
git config user.name "nba-tracker-bot"; git config user.email "actions@users.noreply.github.com"
START=$(date +%s); LIMIT=${LOOP_SECONDS:-3000}; EVERY=${PROPS_EVERY:-120}
save() {
  git add research/props_fd state/props_live.csv state/props_fd_runs.csv 2>/dev/null || true
  git diff --cached --quiet && return 0
  git commit -q -m "Props lines $(TZ=America/New_York date '+%F %H:%M')"
  for i in 1 2 3 4; do
    if git pull --rebase --autostash -q origin main && git push -q origin main; then return 0; fi
    git rebase --abort 2>/dev/null; sleep 5
  done
  echo "Could not save; resetting to the latest saved state."; git fetch -q && git reset -q --hard origin/main
}
while :; do
  git pull --rebase --autostash -q origin main || { git rebase --abort 2>/dev/null; git fetch -q; git reset -q --hard origin/main; }
  T0=$(date +%s)
  timeout 100 python props_shadow.py . snapshot || echo "snapshot failed"
  timeout 100 python props_shadow.py . live || echo "live alerts failed"
  save
  NOW=$(date +%s); [ $((NOW - START + EVERY)) -ge "$LIMIT" ] && break
  WAIT=$((EVERY - (NOW - T0))); [ "$WAIT" -gt 0 ] && sleep "$WAIT"
done
echo "Props loop finished after $(( ($(date +%s) - START) / 60 )) minutes."
