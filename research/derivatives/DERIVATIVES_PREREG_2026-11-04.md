# NBA quarter / half / team-total lines — pre-registration (written Nov 4, 2026, before any results)

## Question
Books mostly derive 1st-half, 1st-quarter and team-total lines from the full-game spread and total. If our full-game models beat
the full-game market, do the derived markets carry the same (or a bigger) edge, because the books' derivation is mechanical?

## Data
- `data/period_history/nba_period_lines.csv.gz` (Action Network: Open, Consensus, DraftKings, FanDuel; game / 1H / 1Q / 2H)
- `data/period_history/nba_linescores.csv` (quarter scores, for grading)
- Full-game predictions: the live spread model (v2 at the opener, 8 PM report leak removed, as in research/spreads/STEP1_NBA_RESULTS.md)
  and the live totals model v4, both scored out of sample as in their own backtests.

## Model (fixed now)
- 1H/1Q spread = full-game predicted margin x league share of margin in that period; 1H/1Q total = predicted total x league share,
  each share estimated on the FIT seasons only, plus a team start-of-game adjustment (team's period share minus league share,
  shrunk toward 0 with k = 20 games), fit seasons only.
- Team totals = (predicted total ± predicted margin) / 2.

## Seasons
- Fit: 2022-23 and 2023-24. Test: 2024-25 and 2025-26. (If DraftKings lines are missing for 2022-23, fit on 2023-24 only.)

## Bet rules (fixed now)
- Edge = model number minus the Open line. Bet when edge >= 1.5 (1H spread), 2.0 (1H total), 1.0 (1Q spread and 1Q total), 2.0 (team totals).
- Grade every bet at the Open line (best case) AND at DraftKings' close (worst case), -110 unless prices are listed.

## What counts as passing
1. Primary: CLV = DraftKings close minus Open, in our direction, > 0 with a 90% bootstrap CI above 0 on the test seasons.
2. Second: units > 0 at the DraftKings close.
3. Accuracy reported alongside.
A market that passes goes live as PROVISIONAL (own record per model version). One that fails is recorded in TRENDS and dropped.

## Side questions (descriptive, no pass/fail)
- How mechanical are the derived lines? Regress each book's 1H/1Q line on its own full-game line; report R² and the residual spread.
- Does the gap between the 1H line and (full-game line x league share) predict the 1H result?
- CLV comparisons across timings are biased toward earlier bets (more time for the line to move); noted, not corrected.
