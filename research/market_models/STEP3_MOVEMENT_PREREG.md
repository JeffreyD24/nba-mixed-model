# Step 3 pre-registration: movement model for NBA totals (DraftKings)

Written Nov 5, 2026, **before** any movement model was fit or any result looked at.

## Question
At any moment before tip, where will DraftKings' total close relative to where it is now?
Target = DK close - DK line at this snapshot. Predicting the move is predicting CLV directly.

## Data
`data/odds_history/nba/` snapshots (every 20 min to 1 h). Every row is one game at one snapshot with **every book's
quote at that same snapshot** (no book's later line is used; this is the step 1 and step 2 timing trap).
Rows: snapshots at least 0.5 h before tip, excluding the final (closing) snapshot.
Each game gets equal total weight (weight 1 / its number of snapshots).

## Inputs (all known at that snapshot)
- Hours to tip; DK move so far (now - DK first seen).
- Book gaps at the same snapshot: Pinnacle - DK, FanDuel - DK, median of all other books - DK, number of books quoting.
- Price lean: DK over price minus under price (American, converted to implied probability), same for Pinnacle.
  ("Price moves come before point moves.")
- Opener-model view (step 2): DK first-seen residual, and the opener model's prediction minus DK now.
  Residuals are walk-forward (14-day refits on earlier dates only), so no future information.
- Not used here: betting splits (2026-27 only), injury news timing (not matched to the minute).

## Models and choice
Ridge-linear and boosted trees. Fit on 2022-23 and 2023-24, choose by game-weighted mean squared error on 2024-25,
refit the chosen one on 2022-23 to 2024-25, score **once** on 2025-26. Also reported: share of the (close - now) error
removed vs predicting no move.

## Bet rule tested on 2025-26 (fixed now)
For each game, walk its snapshots in time order (0.5 h+ before tip). Bet DK the **first** time the predicted move is
**1.5+ points**, on the side the line is predicted to move toward (predicted up -> Over now; down -> Under now),
at DK's line and price at that snapshot. One bet per game.
- **Break-even CLV: +1.07 pts** (NBA full-game totals: result sd 18.0 around the DK close; -110 needs 52.4%).
- **Pass** only if CLV is above +1.07 **and** units are positive (1 unit per bet, actual price, pushes 0). Win rate alongside.
- Pass = PROVISIONAL shadow record in 2026-27 (no alerts), Fable check before anything live. Fail = noted, not bet.
- Exploratory only: thresholds 1.0 and 2.0; bets only 3 h+ before tip; the same test on 2024-25;
  adding our outcome model's edge (Model 3 at the opener report, available only for 2024-25 and 2025-26).
- Known bias: CLV comparisons favor earlier bets (more time to move). Reported by hours-before-tip bucket.

## Addendum (Nov 5, 2026, 3:15 PM ET, before running): feed-compatible variant "movement v1-an"
The Odds API live feed (Pinnacle + 9 books) paused at 6:10 AM Nov 5 (credits used by the props backfill, ~2,089 left).
The free Action Network feed (every minute; DraftKings, FanDuel, Caesars, BetMGM, BetRivers, Fanatics, bet365; no Pinnacle)
keeps running. To bet the movement rule live without Pinnacle, the same model is re-fit with only inputs that feed has:
- Books: DraftKings, FanDuel, Caesars (williamhill_us), BetMGM, BetRivers. Fanatics and bet365 are left out (not in the history).
- Inputs dropped: Pinnacle gap, Pinnacle price lean, Pinnacle present. Everything else as in the no-injury live model.
- Same fit (2022-23..2024-25), same test (2025-26, once), same trigger (1.5 pts), same grading.
- **Goes live as PROVISIONAL (alerts with money, Jeffrey Nov 5)** if its 2025-26 CLV is at or above break-even (+1.07).
  If CLV is above 0 but below +1.07: not pushed, reported to Jeffrey. If CLV <= 0: not used.
