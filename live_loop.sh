#!/usr/bin/env bash
# Polls live in-game lines every 60 seconds while an NBA game is in progress (live.py), saving every 5 minutes.
# Stops when no game is in progress or starting within 45 minutes, or after ~5h40m (GitHub's 6-hour job limit);
# the next scheduled run picks up from there.
set -u
git config user.name "nba-tracker-bot"
git config user.email "actions@users.noreply.github.com"
START=$(date +%s); LIMIT=${LOOP_SECONDS:-20400}; LAST_SAVE=$START

save() {
  [ -d research/live ] || return 0
  git add research/live
  git diff --cached --quiet && return 0
  git commit -q -m "Live lines $(TZ=America/New_York date '+%F %H:%M')"
  for i in 1 2 3 4; do
    if git pull --rebase -q && git push -q; then return 0; fi
    git rebase --abort 2>/dev/null; sleep $((5 * i))
  done
  echo "Could not save; will retry at the next save."
}

while :; do
  python live.py .; code=$?
  NOW=$(date +%s)
  if [ $code -eq 3 ]; then echo "No game in progress or about to start; stopping."; break; fi
  if [ $((NOW - LAST_SAVE)) -ge 300 ]; then save; LAST_SAVE=$(date +%s); fi
  [ $((NOW - START + 120)) -ge "$LIMIT" ] && break
  sleep $((60 - $(date +%s) % 60 + 5))
done
save
echo "Live loop finished after $(( ($(date +%s) - START) / 60 )) minutes."
