# Report watcher — plan and decision rule (written Nov 4, 2026, before any live data)

Approved by Jeffrey Nov 4, 2026 (7:32 PM). Follows `REPORT_SLOT_RESULTS.md`: DraftKings prices ~55% of a report's news in the ~26 min
after it posts (64-71% for noon-6 PM reports); betting before the move was worth CLV about +1.0 to +1.2 on 2+ pt news (an upper bound).
This measures what we can actually get live. **TEST bucket only: no bets, no phone pushes.**

## What runs
- `report_watch.py`, every minute inside `alert_loop.sh` (between the 5-minute checks and after each check), 9 AM-11 PM ET: looks for the
  newest report file (15-minute names `YYYY-MM-DD_HH_MMPM`, and the older hourly name at :30). A new file is downloaded at once, every
  listed player's status compared with the previous report, each change rated with that day's saved model
  (`state/model_<date>.json`: margin and total swing if he sits, times the change in p_miss), and logged to
  `research/report_watch/<game date>.csv` with the minute we first saw it.
- `report_watch_grade.py`, morning run: joins each event with DraftKings' per-minute lines (`research/pregame/`, from `pregame.py`)
  at the report's printed time, first seen, +5, +15, +30 min and the close; writes `state/report_watch_record.csv` and
  `state/report_watch.md`. Both are in the daily health check.

## Events and measures
- Event = a game whose summed news vs the report just before (15-60 min earlier, nothing missed) is 0.5+ pts, spread or total separately.
- Measures: our detection lag (printed time -> first seen); line move per point of news in each window; CLV vs the DK close of a
  hypothetical bet on the news side at first seen / +5 / +15 / +30 for news of 1.5+ pts; win-loss once results are in.

## Decision rule (fixed now; checked at 100 events with 1.5+ pts news per market, or Dec 15, 2026, whichever first)
- **Promote to a PROVISIONAL alert tier** (needs Jeffrey's approval and a Fable review) only if, for 1.5+ pt news, CLV at "first seen"
  is at least +0.77 pts for spreads (step-1 break-even) / +0.33 for totals (line-move break-even), and CLV at +5 is still positive.
- **Speed work first** if CLV at "first seen" is positive but below break-even and our detection lag is over 3 minutes (faster polling,
  or moving the watcher off the GitHub loop).
- **Stop** if CLV at "first seen" is at or below 0: the market is ahead of the published report (reporters), and we record that.
- Too few events by Dec 15: say so, keep collecting, re-check monthly.

## Known limits
- The alert loop restarts every ~50 min and GitHub sometimes starts it late, so some reports will be seen late; those still count (it's
  the real lag). Reports missed entirely are dropped (gap over 60 min).
- A report posted late (after a newer one was already seen) is recorded as seen but not compared, so its news is not logged.
- Players the model has no rating for (rookies, two-way players) are logged but not counted in the news.

## Review
Fable reviewed the code before it went live (Nov 4, 2026): 10 findings fixed (report names, both naming styles in the grader, report order across 12/1 PM, timeouts and atomic state, CDN throttling, late postings, gap filter, health-check levels), then re-checked: safe for the alert loop.
