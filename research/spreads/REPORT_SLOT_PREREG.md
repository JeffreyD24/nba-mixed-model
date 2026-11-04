# Pre-registration: every game-day injury report, one at a time (NBA spreads) — Nov 4, 2026

Written and pushed before the report history finished downloading and before any result. Follows `LINE_MOVE_MODEL_RESULTS.md` (the
pretip report is ~75% priced before it posts; the market learns between noon and 6 PM). Data: `research/injury_history/` (every report
file 10 AM-10 PM ET on game days, 2021-22..2025-26, parsed). Script `analysis/report_slot_test.py`; output `_output.txt`; results
`research/spreads/REPORT_SLOT_RESULTS.md`.

## Question
When a game-day report changes a player's status, how much of that news is already in DraftKings' spread when the report's printed time
passes, how much by the first line we could bet after it, and does betting the news side then beat the close?

## Events
- Per game and team: the 8/9 PM night-before report is the starting state, then every game-day report in order of its printed time
  (`as_of`), up to 30 min before tip. Reports where the team is "NOT YET SUBMITTED" are skipped (state carries over).
- Player value = p_miss(status) x expected minutes / 48 x rating. p_miss from `data/p_miss.csv`. Expected minutes = season-to-date
  minutes per game before the date (any team), else last season's. Rating = last season's RAPM (`analysis/rapm_by_season.csv`) shrunk
  by minutes m/(m+1000), else last season's plus/minus per 48 shrunk the same way (as `missed_value` does). Player names matched with the
  same `key()` normalization the live code uses; unmatched players get 0 and the match rate is reported.
- Event = a report where the team's value changes by 0.5+ pts vs that team's previous report. Home-margin news `N` = -(home change) +
  (away change). t0 = the report's printed time. Only the spread (the ratings have no offense/defense split, so totals are not tested).

## Lines (DraftKings, home margin L = -spread)
`pre` = last snapshot at or before t0; `act` = first snapshot at or after t0 + 15 min (realized lag reported; history is ~hourly);
`close` = last snapshot before tip. Events with `act` after tip are dropped.

## Model and bets
- Build 2021-22, 2022-23; test 2023-24..2025-26; 2026-27 live = lockbox (TEST bucket only).
- Fit on build: `L_close - L_act = a + b x N + c x (L_act - L_pre)`. Remaining move `R = b x N + c x (L_act - L_pre)`.
- Bet the side R points to at the `act` line when |R| >= theta, theta in {0.5, 0.75, 1.0} chosen on build by mean CLV (50+ bets).
  One bet per game (the first qualifying event).
- Break-even CLV: logistic of covering vs CLV at the `act` line on build (as in `LINE_MOVE_MODEL_PREREG.md`).

## Measures
1. CLV (points); 2. units at -110; 3. win %. Per season. Also descriptive absorption for |N| >= 1.0: share of the build-fitted full move
   (slope of `L_close - L_pre_open` on N) in the line at `pre`, `act`, `close`, split by report hour (before noon / noon-3 PM / 3-6 PM /
   after 6 PM) and by status change (to Out, to Questionable/Doubtful, back to Available/Probable).

## Decision rule (fixed now)
- **Pass:** test CLV >= break-even, units > 0, CLV positive in 2 of 3 test seasons -> propose a TEST "report news" tier live, with a
  1-minute report watcher (no bets until approved; Fable review first).
- **Partial:** CLV > 0 but below break-even -> news is real but mostly priced within the hour; Part A live (5-min / 1-min lines) decides
  whether a faster path is worth building.
- **Fail:** CLV <= 0 -> record that DK prices individual game-day reports before a +15 min reaction (at hourly resolution).
Anything added after results is labelled exploratory.
