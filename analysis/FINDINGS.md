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

## Shot quality and shooting luck (Nov 1, 2026)
`nba_shots.py` (1.09M field-goal attempts, 2021-22 to 2025-26, ESPN play-by-play: location, distance, shot type) and
`analysis/shot_quality.py`. Expected make probability from distance, corner/deep three, shot type (dunk, layup, pull-up,
step-back, float...), fit on earlier seasons only (log-loss 0.646 vs 0.692 for league average). "Luck" = actual FG points -
expected FG points, season to date before each game (5+ games).
- Repeatable? First-half vs second-half correlation: a team's own "luck" +0.69 (mostly shot-making skill the location model
  can't see), luck allowed +0.39, shot quality itself +0.80.
- **Spreads: nothing.** Luck gap vs home cover r = -0.002 (4,580 games at the close), r = +0.001 at the open (2025-26).
- **Totals: a small, fairly consistent signal.** Games whose four inputs (both teams' luck for and against) were lucky went
  under, unlucky went over: r = -0.040 (about 2.7 standard errors). Betting it at 5+ points/game of combined luck: closing
  totals 53.2% on 2,095 (2023 50.2%, 2024 55.3%, 2025 55.4%, 2026 52.7%); opening totals 2025-26 54.0% on 879. Most of it
  comes from the luck allowed by the away team. Break-even is 52.4%, so on its own this is thin; the next test is whether it
  improves Model 1's totals when added as a correction (needs Model 1's walk-forward predictions re-run for 2023-26).

## Lineups and player plus-minus from substitutions (Nov 1, 2026)
`analysis/lineup_stints.py`: 188,626 stints (same ten players on the floor) in 6,146 games, 2021-22 to 2025-26, 99.7% of games with
5-on-5 in every stint, with the score change in each (`data/nba_stints_hist.csv.gz`). Player ratings by season from them
(regularized adjusted plus-minus, margin per 48 minutes, `analysis/rapm_by_season.csv`). Sensible at the top (Jokic +17.6 to
+21.9, SGA +14.5 to +16.8), but one season of RAPM only correlates +0.30 to +0.39 with the next (players with 800+ minutes both
years), well below what the model's EPM ratings carry. Next test: whether RAPM (or a blend with EPM) values missing players
better than EPM alone, scored against how the line actually moved on each injury decision (`research/injury_decisions.csv`)
and against game results at the opener.

## Predicting the closing line from what's known at the open (Nov 1, 2026)
`analysis/predict_close.py` (games in `analysis/predict_close_games.csv`; Model 1 walk-forward with the opening injury report,
2024-25 and 2025-26, each season's weights fit on the other season). Inputs: Model 1's edge vs the opener, the opener itself,
injuries out at the open, back-to-backs, season-to-date shooting luck, each team's season-to-date results vs the close.
- **The model's edge already predicts where the line goes.** Correlation with the open-to-close move: totals +0.39, spreads
  +0.19 (all inputs: +0.43 and +0.24). Totals bets at the open with a predicted move of 1.5+: line moved our way 71% of the time
  (against 20-22%), average closing line value +2.3 pts. This is the sharps' money arriving after us.
- Team "hot/cold vs the spread" inputs flipped sign between seasons: noise, not used.
- **Shooting luck sharpens NBA totals.** At the opener, totals where the luck signal points the same way as the model won
  57.5% / 55.1% (edge 1-3, 2025 / 2026) vs 45.0% / 48.3% when it points the other way; at edge 3+, 57.5% / 61.4% vs 52.5% / 56.9%.
  Built into the model as adjusted total = model total - 0.5 x combined luck, edge 3+ at the open:
  | c | 2024-25 | 2025-26 |
  |---|---|---|
  | 0 (current) | 455 bets, 54.3%, +16.5u | 383 bets, 58.7%, +46.5u |
  | 0.5 | 599 bets, 55.4%, +34.8u | 524 bets, 57.3%, +48.7u |
  | 1.0 | 765 bets, 54.1%, +25.4u | 706 bets, 56.5%, +55.7u |
  0.5 was better than the current model in both seasons (+20u over two seasons, 285 more bets). Spreads: no robust gain
  (c 0.25 slightly better in both seasons, larger c worse), so spreads stay as they are.
