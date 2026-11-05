# NCAA men's basketball model: pre-registration (Nov 5, 2026)

Written and pushed **before** any model prediction was compared with a betting line or a result graded.
Data: `ncaab/data/games.csv` from `ncaab/backfill.py` (Action Network scores + Open / Consensus / DraftKings / FanDuel full-game
lines; ESPN neutral-site flag matched by date and final score). DraftKings and FanDuel lines exist from 2023-24 on; 2021-23 has
consensus only.

## Model (Model 1, NCAAM)
Ridge mixed model refit every game day, walk-forward (only games before that date):
team points = mu + offense(team) + defense(opponent) + home court x (1 if home, 0 if neutral, -1 if away... coded per team row) + e,
two rows per game. Offense / defense are random effects shrunk toward a prior: last season's final rating x carryover (0 for a
team with no last season). Games are weighted by recency (half-life in days). Predictions: margin = home points - away points,
total = sum. Non-D1 opponents share one "non-D1" team effect.

Hyperparameters (ridge strength, carryover, half-life, home court is fitted) are chosen **only** by out-of-sample prediction error
of margins and totals (mean squared error vs the actual results, walk-forward) on the 2022-23 season, with 2021-22 as warm-up.
No betting line is used to choose them. Grid: ridge {2, 5, 10, 20}, carryover {0.4, 0.6, 0.8}, half-life days {30, 60, 120, none}.

## Bets
- Bet line: Action Network's Open book (the opener). Close: DraftKings' last line before tip. -110 assumed at the open.
- Edge = model - line (margin vs the home spread, total vs the total). Bet the side the model favors when |edge| >= threshold.
- Excluded from bets (kept for ratings): either team non-D1; neutral flag ambiguous (another game the same date with the same
  final score) or unmatched to ESPN; either team with fewer than 3 games this season.
- Thresholds are chosen on **2023-24 only** (the fit season): candidates 2, 3, 4, 5, 6 pts for spreads and for totals. Chosen =
  the smallest threshold whose 2023-24 CLV is at or above break-even CLV. If none, that market fails without looking further.
- **Test seasons: 2024-25 and 2025-26**, at the chosen threshold, looked at once.

## Measures (in this order)
1. **CLV** = points the line moved toward the bet from the Open to the DraftKings close (primary).
   Break-even CLV = 0.0238 x sd x sqrt(2 pi), where sd = standard deviation of (result - DraftKings close) in 2023-24 for that
   market (the CLV that pays -110 vig under a normal result around the close).
2. **Units** at the DraftKings close at DK's own price (fully bettable, conservative), and units at the Open at -110 (optimistic).
3. Accuracy alongside. 90% intervals by bootstrap over game days.

## Pass rule (per market: spreads, totals)
PASS = test-season CLV >= break-even CLV **and** the 90% CLV interval's lower end > 0 **and** units at the Open > 0.
PASS -> PROVISIONAL live alerts (own record, the standing provisional stop rules), after a Fable review.
FAIL -> test-only tracking this season (recorded, no bet alerts).
Anything else found (by month, conference games, neutral sites, FanDuel vs DraftKings) is descriptive only, noted as such.
