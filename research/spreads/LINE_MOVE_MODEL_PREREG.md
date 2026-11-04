# Pre-registration: NBA line-move model (game-day injury report -> DraftKings spread and total move)

Written and pushed Nov 4, 2026, before any result. Follows the moneyline v2 result (models carry real but tiny information; the line keeps
moving on absences after the open) and the approved news-model handoff (`NEWS_MODEL_HANDOFF_2026-11-04.md`, Part A history item 4 and a
first, coarse version of Part B). Script: `analysis/line_move_model.py`; output `analysis/line_move_model_output.txt`; results
`research/spreads/LINE_MOVE_MODEL_RESULTS.md`.

## Question
Instead of predicting the game, predict the **line move**: after the game-day ("pretip") official injury report lands, how much more will
DraftKings' spread and total move by the close, and can we bet the side the news favors at a line we could actually get?

## Data (all already in the repo)
- `data/training_games.csv`, 2021-22..2025-26: injury value per team from the 8 PM night-before report (`*_open`) and from the pretip report
  (latest game-day report at least 60 min before tip; slot time in `snap_pretip_home`). Value = sum of p_miss x expected minutes / 48 x prior
  EPM, offense and defense parts.
- `data/odds_history/nba_snapshots.csv.gz`: DraftKings spread and total snapshots (~2 per hour in the last 2 h before tip).
- Only games whose open snapshot is the 8 PM / 9 PM night-before report and whose pretip slot is on game day, and with a DK line at every
  time point below. Known limit: `p_miss` (status -> chance of sitting) was estimated on 2022-25; reported, not fixed.

## News (in points, known at the report slot)
- Home-margin news `N_sp = -(dmo_h + dmd_h) + (dmo_a + dmd_a)`, where `d` = pretip value minus 8 PM value (mo = missing offense, md = missing
  defense). Total news `N_tot = -(dmo_h + dmo_a) + (dmd_h + dmd_a)`.
- Intermediate game-day reports (11 AM - 5 PM) are not in the data, so part of N may already be public before the slot. That is what the
  "moved so far" term is for.

## Time points (DraftKings; spread expressed as home margin L = -spread)
- `open`: DK opener (first snapshot). `pre`: last snapshot at or before the slot time. `act`: **first snapshot at or after slot + 15 min**
  (a line we could have bet after a 5-min check; taking the first one after, never a stale one before). `close`: last snapshot before tip.
- Games where `act` is after tip are dropped.

## Model (fit on build seasons only)
`move_after = L_close - L_act = a + b x N + c x (L_act - L_open)`, separately for spreads and totals (OLS).
Predicted remaining move `R = b x N + c x (L_act - L_open)` (the intercept is left out: it is not news).
**Bet** the side R points to, at the `act` line, when |R| >= theta, with theta in {0.5, 0.75, 1.0} pts picked on the build seasons by mean CLV
(needing 50+ bets).

## Seasons
- Build: 2021-22, 2022-23. Test: 2023-24, 2024-25, 2025-26 (these seasons were used in step 3a for the 8 PM slot and for the v2 filters; this
  game-day-slot rule is new). Lockbox: 2026-27 live, as a TEST bucket only.

## Measures (in order)
1. **CLV** in points (close minus act, toward our side). Break-even CLV estimated on the build seasons: logistic fit of win vs CLV for every
   game's home side / over at the `act` line; break-even = CLV where the win chance is 52.38% (-110). Step 1 measured +0.77 for spreads at
   the opener; the totals number is new.
2. Units at -110 (pushes = 0), win %; per season.
3. Descriptive (absorption): for |N| >= 1.5 pts, the share of the full move that is in the line before the slot, at `act`, and at the close,
   scaled by the build-season slope of `L_close - L_open` on N.

## Decision rule (fixed now)
- **Pass:** test-season CLV >= break-even, units > 0, CLV positive in 2 of 3 test seasons -> propose a TEST news tier for 2026-27
  (no bets until approved; Fable review first).
- **Partial:** CLV > 0 but below break-even -> the news is real but mostly priced by +15 min; worth chasing only with a faster path
  (Part A live timing decides). No bets.
- **Fail:** CLV <= 0 or units <= 0 with CLV below break-even -> record that DK prices the game-day report before a 15-min reaction.
Anything added after seeing results is labelled exploratory.
