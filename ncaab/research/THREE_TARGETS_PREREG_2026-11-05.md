# NCAAM three-target tournament: results, DraftKings' opener, the close. Pre-registration (Nov 5, 2026)

Pushed before any entrant is graded. Jeffrey: build models that best predict (A) the game result, (B) DraftKings' opening line and
(C) the closing line, compared with each other and with the books. Data `ncaab/data/all_games.csv`. Every prediction uses only games
before that date. Team rule: no conference id -> "OTHER" (pre-game known, Fable fix of Nov 5).

## Seasons
DraftKings' own openers exist for **2023-24 (fit)** and **2025-26 (TEST, looked at once)**; 2024-25 has ESPN BET openers only
(secondary check, reported, decides nothing). Rating models warm up on all seasons from 2007-08.

## Entrants
Rating models (walk-forward, refit each game date): **M1** Model 1 · **M2** moving scoring level · **M8** conference hierarchy (ridge 10 / 10) ·
**MKT market ratings (new):** the same ridge model fitted to the points implied by past games' CLOSING lines instead of the results
(home implied = (total - spread)/2), i.e. a model of how the market rates each team · **ENS:** least-squares blend of M2, M8 and MKT, weights fit on 2023-24.

A. **Results:** RMSE of predicted margin / total vs the actual result, 2025-26, next to DraftKings' opener and close as predictors.
B. **DraftKings' opener:** RMSE of each entrant (and a blend fit on 2023-24: a + b1 MKT + b2 M2 + b3 M8) vs DraftKings' opening line, 2025-26.
C. **The close** (from DraftKings' opener): C0 close = opener (benchmark); C1 opener + b (M2 - opener); C2 + c (MKT - opener);
   C3 + d (M8 - opener); C4 = C3 plus each term x (conference game, both power conference, Nov-Dec non-conference).
   Coefficients fit on 2023-24 DraftKings rows. Measures on 2025-26: RMSE vs the close (vs C0), correlation of predicted and actual move.

## Betting rule from the best close model (chosen on 2023-24: lowest 5-fold cross-validated RMSE within 2023-24)
Bet DraftKings' opener in the direction of the predicted move when |predicted move| >= k; k = smallest of {0.5, 1, 1.5, 2} whose 2023-24 CLV
>= break-even (spreads 0.63, totals 1.02; from the earlier tournament). Grade 2025-26 once: CLV (primary), units at the opener, units at the close.
**PASS** = CLV >= break-even, CLV 90% low end > 0, units at the opener > 0 -> PROVISIONAL candidate after a Fable review. Otherwise TEST record.
Spreads and totals separately. Every entrant's numbers reported either way.
