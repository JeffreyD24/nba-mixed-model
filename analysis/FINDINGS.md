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

## Holdout season 2023-24 at real DraftKings openers (The Odds API history), Nov 1 2026
Model 1 walk-forward, trained on 2021-22 and 2022-23 only, graded at DraftKings' first posted line (1,113 games; the first
two weeks are being re-downloaded). Edge 3+.
- **Totals hold up:** 590 bets, 54.1%, +19.0u. With the shooting-luck correction (league-relative, 0.5): 659 bets, 54.3%,
  +24.5u. The correction beat the plain model for the third season in a row.
- Totals timing: with the luck correction the edge survives about an hour after the open (+22.9u at 15 min, +24.9u at 30,
  +25.2u at 60) and is mostly gone by the close (+9.7u). Without it, it fades faster (+6.4u at 60 min).
- DraftKings' opening NBA prices were -110 on both sides, so the -120 cap never applied at the open.
- **Spreads fail:** 359 bets, 46.8%, -38.4u; no edge size, home/away or line-movement filter rescues it. Three seasons at
  the open: 2023-24 -38.4u, 2024-25 +17.1u, 2025-26 +2.7u -> 610-573 (51.6%), below the 52.4% break-even at -110.
- Model edge vs open-to-close move: totals r = +0.28, spreads r = +0.16.
Scripts: analysis/validate_2023_24_model.py, analysis/validate_2023_24.py

## Following and copying the sharps (Nov 2, 2026)
Data: every hourly-or-finer snapshot of 10 books, NBA and NHL 2021-22..2023-24 (data/odds_history/{nba,nhl}_snapshots.csv.gz).
Pinnacle = the sharp book. Scripts: analysis/sharp_nba.py, sharp_replicate.py, sharp_nhl.py (outputs in *_output.txt).
- **Who moves first:** DraftKings opens first: NBA median 12.6 h before Pinnacle, NHL about 7 h. At hourly resolution neither
  book reliably leads the other (each "follows" the other ~25-30% of the time within 2 h).
- **NBA: Pinnacle's opener carries no edge over DraftKings.** Betting DK on the side Pinnacle's opener prefers: 374 bets, 50.5%.
  Pinnacle's opener is a little more accurate than DK's (spread MAE 10.34 vs 10.42; totals 14.32 vs 14.44) but by the close
  every book is the same. The sharp information arrives during the day, not at Pinnacle's open.
- **What moves NBA lines (DK open -> Pinnacle close):** injury news after the open (biggest), last-10-game form, season form vs
  the opener, injuries already known at the open (DK under-prices them), rest; sharps fade shooting luck and against-the-spread
  streaks. Totals: injury news, injuries known at open, teams' over/under records, fading shooting luck. Explains ~15% of moves.
- **A "sharp model"** (predict the move from what's known at DK's open; train two seasons, test the third): r = 0.2-0.3 and the
  line moves its way ~60%, but betting it is about break-even (spreads +10.7u on 352 at 1+ pt; totals +3.8u on 1,197). Predicting
  where the line goes isn't enough on its own; our totals model already does this (r = 0.28).
- Combined with our totals model (2023-24, edge 3+): when the sharp model also expects a move our way, 480 bets 55.8% +31.6u vs
  146 bets 50.7% -4.7u. One season; watch, not a rule. It does not rescue spreads (47-48% either way).
- **NHL: Pinnacle disagreeing is a warning.** Shot model moneyline bets at DK's opener, EV 6%+ (1,331 bets, +64.5u): when
  Pinnacle's first price likes our side less than DK did, 260 bets -31.5u (-12%), negative in all three seasons (-4.1, -16.9,
  -10.5); agrees or same: 1,071 bets +95.9u (+9%). Waiting for Pinnacle costs too much (DK's price at Pinnacle's open: +32.4u),
  so the use is a filter when Pinnacle is already posted at alert time (20% of games at DK's open; there: disagree 55 bets -11.4u).
- NHL "follow Pinnacle" (bet DK when Pinnacle's no-vig chance is 2+ pts higher for a side): 1,208 bets +85.7u, positive all three
  seasons, but 1%+ and 3%+ are flat, so not trusted yet.

## Recent form and waiting for Pinnacle (Nov 2, 2026)
- **Last-10-game form** (analysis/form10_test.py): beyond our model, a team's last 10 games vs its season level adds a little to
  the result vs the opener in all three seasons (spreads +0.08/+0.09/+0.13 pts per pt; totals +0.20/+0.16/+0.01). Adding it
  to spreads at weight 0.15: 2023-24 -42.4u -> -39.1u, 2024-25 +3.5u -> +30.0u, 2025-26 -1.3u -> +11.6u (weight picked on the
  same seasons, so optimistic). Totals: no consistent gain. Spreads stay test-only; re-test with a proper recency term in Model 1.
- **NHL, waiting for Pinnacle:** of 1,331 shot-model bets at DK's opener, Pinnacle posted a median 3 h later; 78% (1,033) still had
  6%+ value at DK then (made +24.6u waiting vs +29.5u at the open). The 160 that lost value had made +26.1u at the open (the
  market moved our way). Waiting and betting only when Pinnacle agrees: 835 bets +36.2u, vs +64.5u for betting every open.
- Live recording of Pinnacle + 9 US books every 5 min started Nov 2 (pinnacle_watch.py -> research/live_odds/).

## Recent-form adjustment, adopted for totals (Nov 2, 2026)
`analysis/form_adjust.py`, `form_adjust_results.csv`. Form = a team's last k games minus its season-to-date average. Each test
season's weight is fit only on the OTHER two seasons' Model 1 predictions (residual vs form). Edge 3+ at the opener, both teams 10+ games:
| Totals (from the live luck-corrected model) | 2023-24 | 2024-25 | 2025-26 | Total |
|---|---|---|---|---|
| no form | +21.0u | +30.5u | +53.3u | +104.8u (1,621 bets) |
| last-10 game totals | +34.5u | +39.3u | +66.8u | +140.6u (1,631 bets) |
Better all three seasons; error vs the final score lower in two of three. Last 15 also helped; last 5 and shot-quality form
(no shooting luck) were mixed. Live: weight 0.20 (fit on all three, se 0.034), typical adjustment +/-1.9 pts, applied once both
teams have 10+ games (nba_luck.py -> state/nba_luck.json; alert.py "recent-form adjustment").
Spreads, last-10 margin: better all three seasons (-42.4 -> -38.3, +3.5 -> +6.9, -1.3 -> +16.0) but still -15.4u overall, so
spreads stay test-only; the adjustment (weight 0.11) is applied to the test-only spread tracking.
- Window check (same out-of-season method), totals units over three seasons: none +104.8, last 10 +140.6, last 12 +121.1,
  last 15 +130.7, last 20 +109.7, last 25 +99.8, average of 10 and 15 +142.6, 10 and 15 as two weights +131.4. Every window from
  8 to 20 beats no form; neighbouring windows differ by 10-20u (noise), so last 10 stays. Spreads: all windows still negative.

## Spread autopsy: why NBA spreads lose (Nov 2, 2026)
`analysis/spread_autopsy.py` -> `spread_autopsy_bets.csv`. 1,050 Model 1 spread bets at the opener, edge 3+, 2023-24..2025-26
(both teams 10+ games), wins vs losses.
- **The model goes blind after January.** Oct-Jan: 492 bets, 56%, +36.8u, positive every season (+2.1/+20.2/+14.5).
  Feb-Apr: 558 bets, 45%, -76.9u, negative every season. Regressing results on model and line: the model's weight is 0.42-0.80
  in Oct-Jan and -0.18 to +0.20 in Feb-Apr. Likely cause: the trade deadline, buyouts, tanking and resting change who actually
  plays, and the model's team ratings don't catch up (the line does). Totals don't fade (Feb-Apr 58-59% all three seasons).
- **Home underdogs lose:** 408 bets, 44.9%, -58.6u, negative every season; everything else 642 bets +18.1u. Results come in
  below both the model and the line for home teams (home-court residual -0.1 to -0.7 pts), so the model's home edge is too big.
- 84% of the model's spread bets are underdogs (it rarely disagrees with the favorite).
- Injuries: when our side is missing more player value at the open than the opponent and the model still likes it, 400 bets,
  46.5%, -44.9u (2023-24 and 2024-25 bad, 2025-26 flat): the model under-penalizes injuries to the side it likes.
- Not home dogs AND Oct-Jan: 318 bets, 60%, +48.5u (+10.1/+19.2/+19.3). Found on the same seasons, so it needs a fresh test.
- No pattern: edge size, recent form, back-to-backs, injury news after the open. The line moving against us is the biggest
  single tell (37.7% won), which is what the DON'T BET rule already uses.

## Spread fixes tested (Nov 2, 2026)
`analysis/spread_fixes.py`, `analysis/roster_strength.py`. Each weight fit only on the other two seasons; edge 3+ at the opener.
| Fix | 2023-24 | 2024-25 | 2025-26 | Feb-Apr | Total |
|---|---|---|---|---|---|
| current model | -42.4 | +3.5 | -1.3 | -76.9 | -40.1u (1,050) |
| smaller home court | -40.7 | +0.7 | -3.9 | -73.5 | -43.9u |
| more injury weight | -47.5 | +4.3 | -10.9 | -83.0 | -54.2u |
| roster strength | -34.3 | +11.5 | +12.9 | -39.6 | -9.8u |
| roster + last-10 form | -28.4 | +17.5 | +14.3 | -39.3 | +3.5u (1,058, 52.6%) |
- **Roster strength is the real fix:** rotation value now (minute share x last season's EPM) minus the average the team has played
  with so far this season. Weight 0.57-0.63 pts per EPM point; best error vs results. Halves the Feb-Apr losses: the model was
  missing trades/buyouts/returns. Home court (-0.1 pt fitted) and extra injury weight don't help; home dogs improve only via roster.
- Totals: roster strength doesn't help (+97.9u vs +104.8u); form stays the only totals change.
- Spreads with roster + form are break-even overall (+3.5u), still -28.4u in 2023-24, so spreads stay test-only. Both are now in
  the test-only spread tracking (tracker.py exports roster deltas; alert.py ROSTER_W = 0.57 once both teams have 10+ games).

## Totals autopsy (Nov 2, 2026)
`analysis/total_autopsy.py` (output `total_autopsy_output.txt`). 1,593 live-model totals bets (luck + form), edge 3+ at the
opener, 2023-24..2025-26: 57.4%, +152u. No losing pocket: overs and unders, every edge size, every total level, every month,
back-to-backs, injuries all positive. Only "line moved against us" loses (435 bets, 49.7%, -22.6u), already the DON'T BET rule.
November is weakest (52.9%, +2.1u; luck and form aren't active yet), overs Oct-Jan 53.6% vs Feb-Apr 61.1%.

## NFL autopsy (Nov 2, 2026)
`analysis/nfl_autopsy.py` (output `nfl_autopsy_output.txt`); openers: DraftKings from the odds history (2020-23,
`analysis/nfl_openers.py`), backtest opener (2024-25). Full-game bets at the opener, edge 3+, early-week model, 2020-2025:
- Spreads: 471 bets, 51.0%, -12.8u (+9.7, -15.8, +5.2, -4.2, -5.6, -2.1). Totals: 525 bets, 52.8%, +3.8u (2025 -11.9u).
  No proven full-game edge at the opener.
- Week 15+: spreads 108 bets 41.7% -22.1u (negative 5 of 6 seasons), totals 129 bets 46.5% -14.5u: late-season rest and
  motivation, as with the NBA after January.
- Away spreads -25.9u (negative 5 of 6); betting against a team whose QB is out 40.0%, -13.0u (the model over-penalizes a
  missing QB); outdoor overs 45.8% -16.5u vs outdoor unders 56.6% +14.6u (weather isn't in the model).

## All three seasons at real DraftKings lines (2024-26 odds downloaded Nov 2, 2026)
`analysis/validate_dk_2024_26.py` (output `validate_dk_2024_26_output.txt`). Edge 3+.
- **Totals (live: luck + form):** opener +46.3u / +40.3u / +60.5u (2023-24 / 2024-25 / 2025-26), 1,615 bets, ~57%. Still
  +37 to +55u per season at +60 min; at the close +6.5 / -52.8 / +8.3. Bet within the hour.
- **Spreads (roster + form, test-only):** opener -28.3 / +18.0 / +2.1. Oct-Jan +10.1 / +19.8 / +2.5; Oct-Jan without home
  underdogs +16.1 / +19.3 / +6.7 (355 bets, 58.3%, +42.1u). Feb-Apr -38.4 / -1.8 / -0.4.
- **Sharp-move model filter:** no help out of sample (2024-25: agrees 56.0%, disagrees 58.6%; 2025-26: 59.6% vs 56.8%). Dropped.
- **NHL, Pinnacle's first price disagrees with the shot model:** negative all five seasons (-4.1, -16.9, -10.5, -3.6, -6.9;
  405 bets, -42.0u); agrees or same: 1,573 bets +138.1u. Holds up as a warning signal.

## Oct-Jan vs Feb-Apr spreads, and what the sharps know (Nov 2, 2026)
`analysis/half_compare.py` (output `half_compare_output.txt`). Live spread model (roster + form), DraftKings openers, edge 3+,
2023-24..2025-26: Oct-Jan 530 bets 55.7% +33.2u; Feb-Apr 514 bets 48.2% -40.5u.
- **Tanking:** Feb-Apr, betting a team below .400: 236 bets 44.9% -33.6u (negative all three seasons); same teams Oct-Jan
  56.0% +10.9u. Worst when that bad team has 5+ players out at the open: 182 bets 42.3% -35.0u. Late-season bad teams shut
  players down and play for the lottery; the model prices the absences by EPM x minutes and still sees value that isn't there.
- **The sharp move carries the late-season information.** Feb-Apr, Pinnacle moving 1+ pt against our side: 144 bets 36.8%
  -42.8u (the whole loss). Oct-Jan the same move barely matters (51.2%). Late scratches don't explain it (similar in both halves).
- **Pinnacle's opener vs DraftKings' (Pinnacle posts ~12 h later):** opened against our side: Oct-Jan 114 bets 45.6% -14.7u,
  Feb-Apr 151 bets 43.7% -25.0u (5 of 6 season-halves negative); opened toward us Oct-Jan 276 bets 60.5% +42.8u.
  Same pattern as the NHL Pinnacle rule. (For totals, Pinnacle's opener showed no such signal.)
- Why sharps beat spreads where we can't: their edge is information about who plays and who's trying (rest, tanking, rotations),
  priced through the day; ours is team strength at the open. In Oct-Jan strength dominates, late season motivation does.

## NFL fixes: weather, QB, home, late season (Nov 2, 2026)
`analysis/nfl_fixes.py` (output `nfl_fixes_output.txt`); weather from the nflverse schedule (nfl-mixed-model/data/nflverse_games.csv:
game-time wind and temperature, outdoor/open roofs only). Each weight fit leaving the test season out; opener, edge 3+, 2020-2025.
| Totals | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Total |
|---|---|---|---|---|---|---|---|
| current | +8.5 | -10.1 | +7.4 | +11.4 | -1.4 | -11.9 | +3.8u (525) |
| wind | +11.8 | -5.5 | +11.3 | +12.4 | -2.7 | -4.5 | +22.6u (573) |
| wind + cold + week 15+ shrink | +9.5 | -5.4 | +14.8 | +12.8 | +0.3 | -4.5 | +27.5u (444, 55.6%) |
- Weather helps totals in 4-5 of 6 seasons (lower error too). The week 15+ fit puts ~zero weight on the model, i.e. skip late weeks.
- Spreads: home-field shift and QB-out corrections don't help (-18.6u, -11.1u vs -12.8u). Skipping week 15+: +11.0u (367 bets, 54.0%).
- Still too thin to bet: full-game NFL stays test-only. Live weather would need a game-time forecast (the nflverse values are actuals).

## Betting after Pinnacle posts (Nov 2, 2026)
`analysis/pinnacle_second_chance.py` (NBA, 2023-26), `analysis/sharp_nhl.py` section G (NHL, 2021-26).
- NBA: waiting for Pinnacle and betting DraftKings only when Pinnacle agrees is worse than betting the opener (totals +66.2u vs
  +148.6u; spreads Oct-Jan +13.9u vs +42.2u). "Second-chance" bets (no edge at the opener, edge when Pinnacle posts and agrees)
  lose (totals 197 bets -2.3u, spreads 45 bets -3.0u). Bet the opener; use Pinnacle only to cancel.
- NHL: second-chance bets (EV under 6% at DK's opener, 6%+ at DK's price when Pinnacle posts, Pinnacle agrees): 172 bets,
  +17.2u (+10.0%), positive all five seasons (+1.8, +0.4, +2.5, +7.2, +5.2). Small but consistent.
- Following Pinnacle on its own (no model): NBA loses; NHL mixed by season. No standalone "Pinnacle model".

## Home stands, road trips, travel and time zones (Nov 2, 2026)
`analysis/travel_schedule.py` (output `travel_schedule_output.txt`; per-game features in `travel_nba_games.csv`,
`travel_nhl_games.csv`), `analysis/travel_fixes.py` (output `travel_fixes_output.txt`). NBA and NHL 2021-22..2025-26.
- **Market misses (vs the closing line, consistent across seasons):**
  - NBA games at Denver/Utah go OVER the closing total by +3.2 pts (positive 5 of 5 seasons: +3.5, +0.3, +2.7, +3.8, +5.6).
  - NHL: when only the away team is on a back-to-back, home teams win 4.3 win-% pts more than the closing price says (5 of 5
    seasons); only the home team on a b2b: -4.6 (4 of 5).
  - Teams that flew WEST since their last game do better than priced: NHL -3.6 pts for the home team (4 of 5 seasons),
    NBA home cover -1.8 pts when the away team moved 2-3 zones west (4 of 5).
  - Home stand / road trip length, distance alone, 3-in-4: nothing consistent.
- **Added to the models (weights fit leaving the test season out), at DraftKings openers:**
  - NHL shot model moneyline + away b2b, home b2b, away moved west: +159.6u vs +96.1u on 2,350 vs 1,978 bets (+6.8% vs +4.9%),
    better in 4 of 5 seasons (2023-24 +16.0 -> +5.5), better Brier.
  - NBA totals + altitude: +159.5u vs +147.1u (2 of 3 seasons better). Time zones / away b2b: no gain.
  - NBA spreads: home b2b, westward travel, back from a long trip: no meaningful change.
- NBA totals bets when the away team moved 1+ zone east: 65.9% (352 bets; 64/69/66% by season) vs 55.0% otherwise.

## What "Pinnacle opened against us" means (NBA spreads, Nov 2, 2026)
Pinnacle posts ~5-7 h after DraftKings, usually at DK's number; when it moves off it (median 1 pt) against our side, the
sharp book has already decided our side is overvalued. Those bets (265) are mostly big underdogs (87%, +5.1 pts), weaker
teams (.440), more of OUR players out at the open (4.6 vs 4.0), our team on a back-to-back 19% (vs 7%), 57% in Feb-Apr.
Predicting it at DK's open is weak (AUC 0.60). Inside the live window (Oct-Jan, no home dogs): Pinnacle against 63 bets
50.8% -1.9u (coin flips); toward 204 bets 62.3% +38.5u; same 91 bets 56.0% +6.4u.
