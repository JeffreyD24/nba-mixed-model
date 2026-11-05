# NCAAM Model 3: three targets (result, DraftKings opener, DraftKings close). Pre-registration (Nov 5, 2026)

Pushed before any result. Jeffrey: build models that best predict (A) the game result, (B) DraftKings' opening line, (C) DraftKings' closing line.
Data `ncaab/data/all_games.csv` (built by `ncaab/build_all_games.py`). Everything walk-forward (only games before the date).

## Entrants
- **M2** (moving scoring level) and **M8** (conference hierarchy) from the Model 2 tournament, live-safe team rule.
- **MKT (new): market-implied ratings.** The same ridge team model, but fitted to the points each team was *expected* to score by
  past closing lines (home = (total - spread)/2, away = (total + spread)/2) instead of the points it scored. A model of how the market
  rates teams, i.e. a stand-in for how books build openers. Same knobs as M1 (ridge 5, carryover 0.8).
- **BLEND-A / BLEND-B / BLEND-C (new):** least-squares stacks of M2, M8, MKT (and, for C, the DraftKings opener) fitted on earlier
  seasons only, separately for spreads and totals, each aimed at its own target (result, opener, close).
- Benchmarks: DraftKings opener and DraftKings close (as predictors of the result); the opener (as predictor of the close).

## Seasons
Stacks fit on 2009-2021 with SBR lines as the target stand-ins (SBR open for B, SBR close for C), plus 2024 for the C/B stacks used in 2026.
**Decision seasons: 2023-24 and 2025-26, DraftKings rows only** (ESPN BET 2024-25 reported separately). SBR openers more than 6 pts from
the close are dropped (Fable, Nov 5).

## Measures
A: RMSE vs results (vs the DK opener's and close's RMSE). B: RMSE vs the DK opener. C: RMSE vs the DK close and the share of the
opener-to-close move predicted (R^2 of predicted move on actual move).
**Betting (from C):** bet the DK opener when |BLEND-C predicted close - DK opener| >= X, on the side the close is predicted to move.
X chosen on SBR 2016-21: smallest of {0.5, 1, 1.5, 2, 3} whose CLV >= break-even (spreads 0.63, totals 1.02).
PASS (decision seasons, DK only) = CLV >= break-even AND units at the DK opener > 0 AND CLV 90% low end > 0 -> Fable review before any
PROVISIONAL use. Otherwise TEST record. All entrants reported either way.

## Addendum (after the first run, before this one): MKT-T, a tuned market model
MKT used Model 1's ridge (5), tuned for noisy game results; closing lines are far less noisy, so it was over-shrunk (worst opener RMSE).
MKT-T = the same market model with ridge chosen from {0.05, 0.2, 0.5, 1, 2} by RMSE vs the SBR opener on 2009-2011 only. It then enters
BLEND-B and BLEND-C (rebuilt with MKT-T in place of MKT). Same decision rows and betting rule as above; reported next to the first run.
