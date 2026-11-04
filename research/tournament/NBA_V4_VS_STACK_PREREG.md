# NBA totals: live v4 vs the stack on the same games, 2024-26 (written Nov 3, 2026, ~8:40 PM ET, before running)

**Label: already-seen seasons, descriptive.** v4's pieces (luck weight 0.5, form 0.20, altitude 3.8, luck shrink 15) were chosen on 2023-26,
so this cannot say which is better out of sample. It answers: on the same games, how do they compare on CLV and results, and does the luck term
add to the stack? It is the Tier B test in NBA_PREREG.md ("scored by leave-one-season-out ... labeled already-seen seasons").
Code: `analysis/nba_v4_vs_stack.py`. Output: `analysis/nba_v4_vs_stack_output.txt`.

## Games
DraftKings openers and closes 2023-24 .. 2025-26 (seasons 2024-2026), both teams 10+ games, opener and close present, luck available.
All numbers use results through two nights before the game (the lag fix).

## Numbers compared (all fixed now)
1. **v4** as live: Model 1 (with the night-before injury report, lag 1, trained 2022+ as in analysis/lag_leak_test.py) + luck correction
   (-0.5 x centered combined luck, times n/(n+15), n = fewer games of the two teams) + form (0.20 x both teams' last-10 minus season)
   + altitude 3.8 at DEN/UTA. Bet at edge 3+ (live THRESHOLD).
2. **Stack as tested**: frozen coefficients (data/stack_totals.json, fit 2014-2022) on Model 1 WITHOUT injuries (the tournament's input). Threshold 1.08.
3. **Stack as recorded live**: same coefficients on Model 1 WITH injuries (what stack_record.py does).
4. **Stack + luck, leave-one-season-out**: stack columns (with injury Model 1) plus the centered luck term, all coefficients refit on the other two
   seasons; and the same refit WITHOUT luck (4a) so the luck contribution is a paired comparison.

## Measures
Bets, win %, units at -110, ROI with 90% interval resampling game days; CLV in points (close minus opener in the bet's direction);
same-game overlap of v4 and stack picks; paired MSE gain of 4 over 4a.

## How it will be used
No verdict on replacing v4 comes from this alone (already-seen seasons). The replacement question is decided on the 2026-27 side-by-side record.
