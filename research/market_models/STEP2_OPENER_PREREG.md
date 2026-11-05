# Step 2 pre-registration: opener models for NBA totals

Written Nov 5, 2026, **before** any model was fit or any 2025-26 result was looked at.

## What is being modeled
For each game and book (DraftKings = primary, Pinnacle = second, FanDuel = extra), the **first total seen** in
`data/odds_history/nba/` (The Odds API snapshots). Target = that number. "Opener" means first line seen, not the
true opener (see step 1 limits).

## Features (all known before the first line was seen)
Every feature uses only games played on **earlier dates** than the game being priced.
- Team pace, offensive and defensive efficiency (points per 100 possessions), points for and against: exponentially
  weighted over past games, carried across seasons.
- League scoring level: weighted average of all league game totals on earlier dates.
- Market memory: each team's recent DraftKings **closing** totals (what the market thought of them lately).
- Previous opener errors: each team's recent (final total - DraftKings first-seen total) and (DraftKings close - first-seen).
- Rest: days since each team's last game, back-to-back flags.
- Injuries known at open: `*_miss_off_open`, `*_miss_def_open`, `*_n_out_open` from `data/training_games.csv`.
- Games into the season, and hours before tip when the line was first seen (a control for capture timing).

## Models compared
1. **Naive**: average of the two teams' recent DraftKings closing totals.
2. **Linear**: least squares on all features.
3. **Mixed**: linear plus a team-by-season "total tendency" random effect (ridge-shrunk, i.e. BLUP with one variance ratio).
4. **Boosted trees**: gradient boosting on the same features.

**Choice rule:** fit on 2021-22 to 2023-24, pick the model with the lowest mean absolute error on 2024-25 for each book,
refit it on 2021-22 to 2024-25, and score it **once** on 2025-26.

## Bet rule to test on 2025-26 (fixed now)
Residual R = book's actual first-seen total - the opener model's prediction (the book "opened off its usual process").
- **Bet:** when |R| >= 3.0 points, bet **against** the residual at that book's first-seen total and price
  (R > 0, opened high -> Under; R < 0 -> Over). DraftKings is the bettable test; Pinnacle is graded for information only.
- **Grading order (standing rule):** CLV first (points gained vs the same book's close), units second (1 unit per bet,
  actual price, pushes = 0), win rate alongside.
- **It counts as a pass** only if CLV is positive **and** units are positive on 2025-26. Pass = PROVISIONAL, tracked in
  2026-27 next to v4, Fable double-check before any live alert. Fail = noted in TRENDS/findings and not bet.
- Thresholds 2.0 and 4.0, and the same test on 2024-25 (validation season), are **exploratory** and reported for context only.

## Also reported (descriptive, no bet decision)
- Correlation of R with (close - first seen) and with (final total - first seen).
- Which inputs each book's opener leans on, and how DraftKings and Pinnacle residuals relate.
