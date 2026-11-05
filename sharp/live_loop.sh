#!/usr/bin/env bash
# Run the sharp-money capture about once a minute for ~28 minutes (GitHub's scheduler can't go below 5 minutes, so one job loops).
# Signals are recomputed every 5th pass; results are committed and pushed every 5 passes so a stopped job loses at most ~5 minutes.
set -u
END=$(( $(date +%s) + 28*60 ))
git config user.name "nba-tracker-bot"; git config user.email "actions@users.noreply.github.com"
i=0
while [ "$(date +%s)" -lt "$END" ]; do
  START=$(date +%s); i=$((i+1))
  if [ $((i % 5)) -eq 0 ]; then python sharp/live_capture.py . || true; else python sharp/live_capture.py . --no-signals || true; fi
  if [ $((i % 5)) -eq 0 ]; then
    git add sharp/live
    if ! git diff --cached --quiet; then git commit -q -m "Sharp money live $(TZ=America/New_York date '+%F %H:%M')"; for k in 1 2 3 4 5; do git pull --rebase -q && git push -q && break; sleep $((RANDOM % 10 + 3)); done; fi
  fi
  SLEEP=$(( 60 - ($(date +%s) - START) )); [ "$SLEEP" -gt 0 ] && sleep "$SLEEP"
done
python sharp/live_capture.py . || true
git add sharp/live; git diff --cached --quiet || { git commit -q -m "Sharp money live $(TZ=America/New_York date '+%F %H:%M')"; for k in 1 2 3 4 5; do git pull --rebase -q && git push -q && break; sleep 5; done; }
