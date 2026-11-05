# NBA 1st-quarter lines from who actually starts — pre-registration (written Nov 5, 2026, before any results)

## Why
The derivatives test (Nov 4) found DraftKings' 1Q lines are a near-exact fraction of the full-game line. That fraction can't know which
five players start. Starters play most of the 1st quarter, so a team whose real starting five is stronger or weaker than its usual
rotation should be mispriced in the 1Q market even when the full-game line is right. Starting lineups are announced ~30 minutes
before tip, so the bet is made at (or very near) the DraftKings close.

## Data
- `data/nba_stints_hist.csv.gz` (every on-court stint 2021-22..2025-26: the 10 players, seconds, points each side)
- `data/external/nba_box/player_games_2012_2026.csv.gz` (starter flags; they match the first stint in 500/500 checked games)
- `data/period_history/` (Action Network: DraftKings 1Q spread/total + prices, quarter scores), DraftKings from 2023-24 on.

## Model (fixed now)
- Player offense and defense ratings: ridge regression on stints (one row per stint per side; offense players +1 in O columns,
  defense players +1 in D columns; target = that side's points per 12 minutes; weight = seconds). Stints from earlier seasons weighted
  0.5 per season back. Refit every 7 days using only stints from games BEFORE that week; ridge penalty chosen on 2023-24 only from
  {50, 150, 400, 1000} by 1Q squared error.
- Starters' 1Q prediction: home 1Q points = league 1Q rate + sum(home starters' O) + sum(away starters' D) (and the mirror for away).
  1Q margin and 1Q total follow.
- Signal = starters' prediction minus what the DK close line implies:
  spread gap = starters' 1Q margin + DK 1Q home spread; total gap = starters' 1Q total − DK 1Q total.
  Calibrate on 2023-24 only: y (home cover margin vs the DK 1Q line, or 1Q total minus the line) = b × gap; b by least squares.
- Bet when |b × gap| ≥ 1.0 point (spread and total). Price = DraftKings' listed 1Q price (−110 if missing).

## Seasons
Fit/calibrate: 2023-24. Test: 2024-25 and 2025-26.

## What counts as passing (both needed)
Because the bet is placed at about the close, CLV is ~0 by construction and is NOT the measure here (noted deviation from the usual
CLV-first rule).
1. Primary: out of sample, the starters' gap predicts the result beyond the DK close: squared-error gain
   mean(y²) − mean((y − b·gap)²) > 0 with a 90% bootstrap CI (by date) above 0, on all test games.
2. Second: the bets win above break-even at DK's prices (52.4% at −110) and units > 0.
Accuracy reported alongside. A pass goes live only as PROVISIONAL after a Fable check.

## Side questions (descriptive)
- Games where a team's starting five differs from its previous game's (a "surprise" start): is the gap bigger there, and is the
  DK 1Q line slower to adjust?
- Does the same gap predict the 1st-half and full-game cover too (i.e. is it a 1Q effect or general)?
