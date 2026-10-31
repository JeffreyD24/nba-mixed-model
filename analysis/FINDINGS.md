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

## 2026-10-30: by coach (coach-by-date table `data/coaches.csv`, from Wikipedia season pages; 2022-23 hand-entered)
Script: `analysis/coach_rotations.py`. Close games (final margin 10 or less), interim coaches excluded.
- A coach's back-to-back habit doesn't repeat from one season to the next (70 coach pairs): correlation +0.09 for 2nd-half bench share,
  0.00 for starters' 4th-quarter minutes, +0.13 for the top player's 2nd-half minutes. Same answer as the team-level test: no reliable edge.
- A coach's overall rotation style is fairly steady year to year (102 pairs): +0.48 bench share, +0.48 starters' 4th-quarter minutes,
  +0.63 top player's 2nd-half minutes (most of these are the same coach with the same team, so roster is mixed in).
- Coaches who changed teams (only 9 cases with 20+ close games at each): 2nd-half bench share followed the new team's roster more than the coach
  (+0.39 vs +0.18); starters' 4th-quarter minutes followed the coach more (+0.27 vs -0.34). Nine cases is far too few to rely on.
- Takeaway: rotation style is real but comes from both coach and roster; back-to-back-specific habits are noise for teams and coaches alike.

## 2026-10-31: bet sizing by edge (backtest, live model setup vs opening lines, 2024-25 + 2025-26, 1,710 bets with edge 3+)
- Bigger edges did not win more often: 3-4 pts 53.8%, 4-5 52.3%, 5-6 57.2%, 6-8 54.3%, 8+ 53.4%. Fitted slope +0.22 percentage points
  per extra point of edge (essentially flat). Against closing lines over 12 seasons, every edge bucket won 49-50%.
- Staking plans (units won / risked / return per unit / worst drawdown): flat 1u 54.0 / 1,710 / 3.16% / 41.5;
  1-1.5-2u by edge 78.9 / 2,454 / 3.21% / 70.6; 1-2-3u 103.7 / 3,199 / 3.24% / 99.6; edge/3 99.6 / 2,876 / 3.46% / 75.5.
- The bigger totals come only from risking more; return per unit is the same (1-1.5-2u vs flat: +0.06%, 95% range -1.1% to +1.2%,
  better in 55% of resamples), while the worst drawdown grows in proportion. Same as betting about 1.4u flat on everything.
- Takeaway: don't scale stakes by edge size with this model. Set one unit size from bankroll (about 1% or less) and keep it flat.
  Revisit if live results ever show bigger edges winning more often.

## 2026-10-31: how fast the edge disappears, and which way the line moved (Model 1, night-before report, 2024-25 + 2025-26)
Lines between open and close are interpolated (open + fraction × (close − open), rounded to the half point), so this assumes
the line moved steadily one way; the live 5-minute history and the Bet Timing sheet will check it.
- Edge 3+: opening line 53.3% spreads / 54.6% totals; halfway 48.7% / 48.2%; close 48.8% / 48.0%. Raising the bar to 4, 5 or 6+
  didn't rescue halfway bets (e.g. edge 5+ halfway 51.4% / 48.0%).
- By direction (halfway line, edge 3+ at that line): moved **against** the bet 43.4% (854 bets, −146u); not moved 48.7%;
  moved **toward** the model 56.0% (550 bets, +38u). Against: 42.3/45.5% (2024-25 spreads/totals), 40.7/43.5% (2025-26);
  toward: 63.4/51.1%, 60.6/56.5%. Size of the move against: 0.5 pt 45.0%, 1 pt 45.2%, 1.5-2 43.5%, 2+ 42.5%.
- NFL backtest (2023-25), same test: against 46.6% / 48.7% (spreads/totals), toward 55.1% / 52.5%.
- Applied: alerts now flag CAUTION after any half-point move against the bet (was 3 points), in the NBA and NFL trackers.
- Takeaway: bet at or very near the opener; a later line that has moved against the model is the market knowing something.
  A line that moved toward the model with edge left is the best later bet.
