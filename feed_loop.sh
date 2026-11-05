#!/usr/bin/env bash
# All-markets odds feed (DraftKings + FanDuel): one odds_feed.py tick a minute for ~50 minutes, commit the new files every 5 minutes.
# Own workflow and lock, so it never delays the alert loop. Only research/feed/ is committed (changes only, one small file per 5 minutes).
set -u
git config user.name "odds-feed-bot"
git config user.email "actions@users.noreply.github.com"
START=$(date +%s); LIMIT=${LOOP_SECONDS:-3000}; LAST_SAVE=0
save() {
  git add research/feed 2>/dev/null
  git diff --cached --quiet && return 0
  git commit -q -m "Odds feed $(TZ=America/New_York date '+%F %H:%M')"
  for i in 1 2 3 4; do
    if git pull --rebase --autostash -q && git push -q; then return 0; fi
    git rebase --abort 2>/dev/null; sleep $((3 + i * 2))
  done
  echo "Could not push the feed files this time; they stay for the next save."
}
while :; do
  T0=$(date +%s)
  timeout 100 python odds_feed.py . || echo "feed tick failed; next minute."
  NOW=$(date +%s)
  if [ $((NOW - LAST_SAVE)) -ge 300 ]; then save; LAST_SAVE=$NOW; fi
  [ $((NOW - START + 60)) -ge "$LIMIT" ] && break
  S=$((60 - (NOW - T0))); [ "$S" -gt 0 ] && sleep "$S"
done
save
