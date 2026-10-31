# Research findings log

## 2026-10-30: second-half rotations and back-to-backs (2021-22 to 2025-26, 6,148 games)
Data: `research/minutes_history/` (minutes by quarter, games within 1 minute of the box score), results from `data/training_games.csv`.
Close games = final margin 10 or less.

- League-wide, back-to-backs don't change second-half bench use: bench share of 2nd-half minutes 33.9% rested vs 33.9% on back-to-backs (close games).
- The score does: bench share of 2nd-half minutes is 33% in games decided by 0-5, 34% by 6-10, 38% by 11-15, 44% by 16-20, 52% by 20+.
- A team's back-to-back effect doesn't persist: early-season vs late-season effect, same team and season (coach almost always the same),
  correlation -0.01 for 2nd-half bench share, -0.03 for starters' 4th-quarter minutes, -0.14 for the top player's 2nd-half minutes (85 team-seasons).
  Season to next season: +0.16 (94 pairs). The extreme teams in any one season are mostly noise.
- A team's overall rotation style does persist: early vs late season correlation +0.66 (2nd-half bench share), +0.65 (starters' 4th-quarter minutes),
  +0.67 (top player's 2nd-half minutes).
- Takeaway: "coach X plays his bench more in 2nd halves on back-to-backs" isn't supported at team level. The stable signal is each team's general
  rotation style and the blowout effect; next test is whether 2nd-half totals, team totals and player props price those in.
- Not yet done: split by coach name (needs a coach-by-game table; ESPN's historical coach data is wrong, Wikipedia not yet reachable).
