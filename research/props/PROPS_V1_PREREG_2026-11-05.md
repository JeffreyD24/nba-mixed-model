# NBA player props v1 (points, rebounds, assists, threes) — pre-registration (written Nov 5, 2026, before any results)

Only data coverage has been looked at (which books/markets/snapshots exist), not any outcome or edge.

## Data
- Lines: `data/props_history/nba/` (The Odds API; DraftKings, FanDuel, Pinnacle, BetMGM, Caesars, BetRivers), 2024-25 and 2025-26,
  'am' = 11 AM ET snapshot (the bet), 'close' = 10 minutes before tip. One main line per player per book.
- Results: `data/player_stats/` (ESPN box scores 2021-22..2025-26: minutes, points, rebounds, assists, threes).
- Full-game DraftKings opener total (`data/odds_history/nba_open_close.csv`) for pace.

## Model (all settings fixed now; nothing tuned on prop lines except the two items marked FIT)
For player i before game g, using only games before g's date:
- Minutes: exponentially weighted mean of minutes in games played this season (half-life 5 games), with last season's minutes per
  game as a prior worth 5 games (league-average bench minutes, 18, if no last season). Players with < 3 games this season: skip.
- Per-minute rate for each stat: empirical-Bayes / mixed-model shrinkage — (recency-weighted stat + 150 × prior rate) /
  (recency-weighted minutes + 150), recency half-life 20 games; prior rate = last season's rate if 300+ minutes, else the league rate.
- Opponent factor: opponent's stat allowed per 48 minutes this season vs the league, shrunk with k = 15 games (multiplicative).
- Pace factor (points, assists, threes): DraftKings full-game opener total / that season's average opener total. Rebounds: none.
- Mean μ = minutes × rate × opponent factor × pace factor.
- Distribution: negative binomial with mean μ and one dispersion per stat, estimated on 2023-24 box scores only (no prop data).
  P(over line) = 1 − CDF(floor(line)).
- FIT on 2024-25 only: blend weight w in p = w × p_model + (1 − w) × p_market (p_market = DraftKings 'am' two-way no-vig,
  FanDuel if DK missing), chosen by log loss on 2024-25 outcomes.

## Bet rule
- For each player-market-side at 11 AM: price = the better of DraftKings and FanDuel for that side (both are where we bet);
  EV = p × decimal price − 1. Bet if EV ≥ 5% (3%, 8%, 12% reported descriptively only). One side per player-market.
- Players who don't play are voided (as the books do).
- Test season: **2025-26** (fit 2024-25). Units at the 11 AM price, 1 unit each.

## Measures and what counts as passing (both needed)
1. **Primary — closing-line EV (beats the vig by construction):** for each bet, the close no-vig probability of our side at our line
   (same book; if the close point moved, converted with a normal approximation using the model's sd), times our decimal price, minus 1.
   Pass = mean > 0 with a 90% bootstrap CI (by date) above 0. Break-even is 0 here, since the price paid is inside the measure.
2. Second: units > 0 on 2025-26.
3. Accuracy alongside: log loss of the model, the market close and the blend on 2025-26.
A pass goes live only as PROVISIONAL (own record), after a Fable check. A fail is logged in TRENDS.

## Descriptive (no pass/fail)
- By stat, by book (DK vs FD), by side (overs vs unders), by player tier (minutes 30+, 20-30, under 20), by whether the line moved
  toward us, and Pinnacle-close CLV where Pinnacle has the line.
- CLV comparisons across timings favor earlier bets (more time for the line to move); noted, not corrected.
