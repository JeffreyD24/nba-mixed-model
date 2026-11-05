# Research findings log

Master log for all three sports, newest first. Rules for what goes here and how: `CLAUDE.md` at the root of each repo (RULE 1:
every test, finding, correlation, causal claim, lead, idea and decision gets an entry, committed the same session).

## 2026-11-05: NBA props — past prop lines found; unders rule; props v2; v1b timing [TEST] [DATA] [DECISION]
- Data: free past prop lines from BettingPros' public web API, Dec 2021 – Nov 2026 (closes per book + opener; 2.6M book-lines),
  `data/props_history/bettingpros/`; sources searched and ruled out: research in claude/prop_history_sources_2026-11-05.md (Project).
- Unders at the best of DK/FD/MGM/Caesars close (pre-registered): 2022-25 pooled −1.67% [−2.08, −1.25], 0/3 seasons positive → fail.
  The close over-lean is steady every season (no-vig over 49.4–49.6% vs hit 48.0–48.6%) but smaller than the vig.
- Props v2 (injury-aware minutes, pre-registered): letter-pass on Test A 2024-25 (info coef +0.103 [+0.073, +0.133], +8.7u), but
  the Fable review found the bets were FanDuel-vs-DraftKings closing gaps (often stale lines; no-model rule +61u, model-needed bets
  −50u) and minutes double-counted absences. Not live; v2.1 fix list in research/props/PROPS_V2_RESULTS_2026-11-05.md.
- Props v1b timing: at 11 AM (synchronized Odds API snapshot, 2025-26) the profit is model-driven (model-needed bets +54.8u / +110.3u,
  market-only ≈0u); at the close over 4 seasons the same model nets ≈0. Morning edge, priced out by tip. Model information beyond the
  close is real but small (coef ≈ +0.1, every season).
- Decision: nothing new goes live. Per RULE 2 the current season is not the test: the next v1b test uses PAST seasons at an early
  price — BettingPros' opening lines (`open_line`/`open_price`/`open_time`, 2022-25) — under the negative-CLV extra checks
  (research/PROVISIONAL_BETS.md, added today). The 11 AM FanDuel paper record keeps running only as a pipeline/record check.
- research/props/UNDERS_RULE_RESULTS_2026-11-05.md, research/props/PROPS_V2_RESULTS_2026-11-05.md,
  research/props/reviews/FABLE_REVIEW_PROPS_V2_2026-11-05.md

## 2026-11-05: Can a results-only model ever beat the closing line's accuracy? (NCAAM, all sports) [OBSERVATION] [DECISION]
- Question (Jeffrey): if we keep building models with new weights, will we get more accurate than DraftKings at the close?
- Evidence: 10+ NCAAM model variants (Model 1, M2, M4, M8, M10, MKT, ENS, stacks) across 2007-26: the closing line is the most accurate
  predictor in every season. TEST 2025-26 spread RMSE: best model ENS 11.47, DK opener 11.27, DK close 11.22 (totals 17.24 / 17.18 / 16.96).
- Read: a model built only from past scores uses a subset of the information already in the close (scores, form) and lacks the rest
  (injury and lineup news, sharp money). Better weights approach the close, never pass it. Both errors are mostly irreducible game noise
  (~11 pts on a college spread), so the real gap is small and the target is the "excess error" above that noise.
- Decision (Jeffrey + Claude): (1) build the best possible base model, which must include the market (our ratings blended with opener /
  Pinnacle / line movement); (2) add information the close lacks or gets late: player lineups and minutes (from ESPN box scores), inferred
  injuries (college has no official reports: absences show in minutes), travel and rest; (3) measure every step on accuracy vs the close
  and the beat-the-close slope. Box score backfill 2007-27 started (`ncaab/espn_boxscores.py`, workflow `ncaab-box.yml`).
- [IDEA] Inferred injuries: a player whose minutes drop to 0 without news is information books react to late; test once the box data lands.

## 2026-11-05: Record-everything rule (all sports) [DECISION]
- Jeffrey: every test and every inference, lead, association, correlation, causal claim and idea gets saved in an organized way.
- Decision: `CLAUDE.md` added to nba/nhl/nfl-mixed-model (loaded at the start of every session in those repos) with the rule, where
  each kind of record goes, the entry template and TYPE labels ([TEST] [OBSERVATION] [CORRELATION] [CAUSAL] [LEAD] [IDEA] [DECISION]).
  This file stays the master log; open ideas also go in each repo's `research/IDEAS_AND_CHECKLIST.md`.

## 2026-11-05: Saved build products; never rebuild what exists (all sports) [DECISION]
- What happened: the 2021-26 DK predictions and the 2015-2021 goalie-model predictions (built Nov 3-4) had only lived in the
  gitignored `_tmp/` folder, so both were rebuilt from scratch today for the puck line tests.
- Decision (Jeffrey): RULE 4 in CLAUDE.md (all three repos). Build products go in `derived/` (gzipped, tracked) with a row in
  `derived/MANIFEST.md`; scripts restore them with `derived.py` before building. NHL set up and saved: dk_holdout 2022-2026,
  oos_games, oos_games_g, gr_G1 predictions 2015-2021 (4.8 MB). Checked: both puck line tests reproduce exactly from the saved files.

## 2026-11-05: Separate EV bars for -1.5 and +1.5 puck lines, tested on past seasons (NHL) [TEST] [LEAD] [CORRELATION]
- Question: should +1.5 puck lines get a lower EV bar than -1.5 (lead from the 1-point band test)? Tested now on past seasons (RULE 2).
- Data / method: pre-registered (nhl-mixed-model research/spreads/PL_SIDE_BARS_PREREG.md, 87f5e0b). T1 leave-one-season-out on DK
  openers 2021-26; T2 shot model with goalies on 2014-15..2020-21 at SBR closing puck lines; T3 same seasons at an APPROXIMATE
  opening puck line rebuilt from SBR's opening moneyline (SBR stores no opening puck line).
- Result: T1 picked a 4% +1.5 bar in all 5 folds; per-side bars +98.5u vs shared +66.2u, better in 4/5 folds. T2: everything loses at
  the close. T3: +1.5 at 6-9% 884 bets +21.2u (+2.4%, 5/7 seasons), +1.5 at 9%+ 1,293 bets +5.5%; -1.5 at 6-9% 87 bets +4.1%,
  -1.5 at 9%+ 139 bets -12.2%.
- Read: verdict by the written rule **NOT SUPPORTED** (criterion 2 failed: +1.5 6-9% ROI did not beat -1.5's, on 87 bets). The rebuilt
  price is off by ~3.2 implied-prob points per game with a home/away bias, so T3 is direction only.
- [CORRELATION] +1.5 bets were profitable at every band 6%+ in both data sets; -1.5 only at 9%+ on DK and not on older seasons.
- [LEAD] -1.5 at 9%+ may be weaker than the DK record says. Next: fix the rebuilt-price bias (per home/away mapping), re-run, new prereg.
- Decision: nothing changes; puck line bar stays 9% for both sides. Do not re-suggest per-side bars without new evidence.
- Files: nhl-mixed-model analysis/pl_side_bars.py, analysis/pl_side_bars_output.txt, research/spreads/PL_SIDE_BARS_RESULTS.md.

## 2026-11-05: The current season is not a test season (all sports) [DECISION]
- Jeffrey: stop suggesting "re-test on this season" when past seasons can answer it. Added as RULE 2 in CLAUDE.md (all three repos):
  test now on older seasons, leave-one-season-out, or reconstructed inputs; the live season only when none of those is possible,
  with the reason recorded here.

## 2026-11-05: NHL puck line EV in 1-point bands at the DK opener (NHL) [TEST] [LEAD]
- Question: the Nov 4 audit lumped puck lines at EV 6-9% (514 bets, -11.1u) and moved the bar to 9%. Is 8-9% any better than 6-8%?
- Data / method: shot model walk-forward predictions at DK's opening puck line (+/-1.5), 2021-22..2025-26, one-day info lag, better
  EV side per game, 2nd night of a back-to-back removed. Same predictions as `rule_audit_nhl.py` (reproduces it: 6-9% 513 bets -12.1u).
- Result (all puck lines): 6-7% 203 bets -1.7%; 7-8% 165 -3.0%; **8-9% 145 bets 49.0%, -3.8u (-2.6%), negative 3 of 5 seasons**;
  9-10% 98 +33.6%; 10-12% 193 +20.8%; 12-15% 165 -5.8%; 15%+ 280 +8.6%. EV 8%+ 881 bets +84.0u (+9.5%) vs 9%+ 736 bets +87.8u (+11.9%).
- By side: -1.5 bets at 8-9% 80 bets +2.4% (6-8%: clearly negative); +1.5 bets at 8-9% 65 bets -8.9% (but +1.5 at 6-7% was +9.3%).
- Read: 8-9% looks like the rest of 6-9%, not like 9%+. Lowering the bar to 8% adds 145 bets and loses units. The bands above 9% are
  not monotone (12-15% loses), so differences between single 1-point bands are mostly noise: a 145-bet band at these prices has a
  standard error of about +/-10% ROI. The 9% cutoff itself was chosen on these same seasons (in-sample).
- [CORRELATION] Within 9%+, ROI does not rise with EV; higher model EV is not reliably more profit at the top end.
- [LEAD] The -1.5 and +1.5 sides may need different bars (+1.5 at 6-8% was mildly positive, -1.5 at 6-8% clearly negative).
  In-sample and small. Corrected the same day: per RULE 2 (CLAUDE.md) it is tested now on past seasons, not on 2026-27
  (nhl-mixed-model research/spreads/PL_SIDE_BARS_PREREG.md).
- Decision: nothing changes; puck line bar stays 9%.
- Files: nhl-mixed-model `analysis/pl_ev_bands.py`, `analysis/pl_ev_bands_output.txt`.

## 2026-11-05: Goalie announcements flipping NHL bet alerts; alerts now show EV by starter (NHL) [OBSERVATION] [DECISION]
- Observation: UTA -1.5 (+210) alerted 12:27 PM at EV +10.2% with Vejmelka expected (model's goalie mix: Vejmelka 60%, Cossa 40%).
  Cossa was confirmed 13 min later; EV fell to +8.9%, under the 9% bar (DON'T BET 12:40 PM). Jeffrey had already bet it at +205.
- Observation: SJ @ MIN, MIN -1.5 (-108), alerted at EV +12.8% with Wallstedt expected; with Pickard it would be +3.3% (not a bet).
  ANA @ CGY over 6.5 (+100), EV +6.4% with Wolf: Cooley +3.1% (not a bet), Sergeev +6.7%; ANA Brossoit vs Husso and SJ
  Nedeljkovic vs Askarov moved EV under 1 point. Some backup starts swing a bet more than any other input; most don't.
- Decision (Jeffrey): bet alerts show "EV by starter" for every goalie not yet confirmed (each likely starter with 10%+ share,
  ✅ if still a bet at the alert's price). Removed from bet alerts: line history, injury news, missing skaters, schedule note,
  running record, record bucket and projected score (all still used by the model and logged). nhl-mixed-model `alert.py`, commit 5a5dc96.
- [IDEA] Bets whose EV clears the bar under only one possible starter could wait for confirmation, or be graded as their own
  group. Test: in the backtests, split opener bets by whether the bet survives every likely goalie, and compare records.

## 2026-11-05: Market models step 3, movement model for DK NBA totals (pre-registered, fd8a220)
- Boosted model of DK close - DK now from same-snapshot inputs removes 6.7% of the error vs "no move" on 2025-26.
- Bet the first time the predicted move is 1.5+: 2025-26 573 bets, **CLV +1.52 ± 0.13 (break-even +1.07), -8.7u, 51.8%**
  (expected 53.3%, -0.7 sd). 2024-25: CLV +2.11, +42.3u. Fails the written rule on units: not bet; shadow record proposed.
- Strongest inputs: step-2 opener residual (line comes back), FanDuel and other-book gaps, momentum, Pinnacle price lean. Pinnacle's number adds little.
- **CLV check (exploratory, 5,643 games 2021-26): 1 pt of CLV = +2.2% win rate in NBA totals, every season; the DK close is fair and +1.07 is the right break-even.**
- Exploratory: adding Model 3's edge (fit 2024-25 only) -> 489 bets CLV +1.83, +20.2u on 2025-26.
- research/market_models/STEP3_MOVEMENT_RESULTS.md

## 2026-11-05: Market models step 2, opener models for NBA totals (pre-registered, d08f49b)
- A mixed model (pace x efficiency, recent DK closes, league scoring level, injuries at open, team-season effects) predicts each book's
  first-seen total within 2.41 (DK), 2.52 (Pinnacle), 2.50 (FanDuel) pts on 2025-26. Beat linear, boosted trees and a naive baseline.
- Bet against a 3+ pt DK residual: **fails.** 2025-26 381 bets, CLV +1.00 (break-even +1.07), -18.5u, 49.9%. 2024-25 was +2.12, +33.2u.
- The residual predicts **movement** (corr with close-open -0.39 / -0.18) but not the result (-0.12 / +0.04). Becomes a step-3 input.
- DK and Pinnacle residuals move together (0.87): shared deviations are information we lack, not book mistakes; they did worst.
- Process: the prereg missed its break-even CLV line (now +1.07 for NBA full-game totals); verdict unchanged.
- research/market_models/STEP2_OPENER_RESULTS.md

## 2026-11-04: Quarter/half/team-total lines from the full-game models (pre-registered)
- Backfilled every NBA date 2021-26 from Action Network (DK/FD period lines from 2023-24 on). Fit 2023-24, test 2024-26.
- 1H total, 1Q spread and 1Q total pass the written rule (CLV > 0, units > 0 at DK close) but their CLV (+0.04 to +0.20) is far below
  break-even (+0.48 to +0.70). Not bet; shadow records only. Team totals: CLV +0.64 (break-even +0.67), +51u at the opener, but it's the
  full-game totals edge split in two, so bet the full total instead.
- DK's 1H/1Q spreads are a near-exact fraction of the full spread (R² 0.99/0.98) and the fraction is right: no edge from the derivation.
- Process fix: every pre-registration now states a break-even CLV, not just CLV > 0.
- research/derivatives/DERIVATIVES_RESULTS_2026-11-04.md

## 2026-11-04: Home-dog lean + injury news stack; live test-only log
- **Stack check (pre-registered, nfl-mixed-model research/spreads/STACK_HOMEDOG_NEWS_PREREG.md 4941760; results 503f5e2): stop.** At the DK line right after the final report: model home-dog picks 182 bets CLV +0.12; news toward the home dog 84 bets +0.26; both 20 bets **CLV +0.42, -4.7u** (break-even +0.64). The signals add roughly one for one but stay below break-even. Most of the home-dog CLV is gone by Friday (Monday-line +0.29 to +0.48 vs report-time +0.12); news against the model's home dog erases it (CLV -0.19).
- **Live (approved, Fable-checked, commit bab0dbd):** `homedog_test.py` in the morning run records the DK spread minutes after each Monday lock and tags home dogs with model edge 3+; grades CLV to the DK close. TEST-only: no alerts, not in any bet record. File state/homedog_test.csv; registered in the health check (216 h) and config/thresholds.csv. First tagged week: week 10 (locks Mon Nov 9).

## 2026-11-04: Spreads step 3 for NHL and NFL; NHL moneyline split into EV buckets
- NHL moneyline: Jeffrey kept EV 4-9% bets; they are now recorded and graded separately from 9%+ (`ML_EV_SPLIT`, `state/ml_ev_buckets.csv`).
- NHL step 3 (nhl-mixed-model `research/spreads/STEP3_NHL_GOALIE_RESULTS.md`, prereg 1fc0e04): game-day model with actual starters adds to the DK price
  1 h before puck drop (w +0.45 [+0.30, +0.59]), but CLV can't be positive that late and the model's skater lineup has look-ahead. No tier, no DON'T BET.
  Opener ML bets whose own goalie was a surprise: CLV -0.98% (vs +1.02%). Proposed: a TEST-only live re-check at goalie confirmation.
- NFL step 3 (nfl-mixed-model `research/spreads/STEP3_NFL_FINAL_REPORT_RESULTS.md`, prereg 66aaaaa): non-QB final-report news vs the close, slope +0.37
  [-0.19, +0.89]: dropped as a bet trigger; bets at the post-report line CLV +0.16 vs break-even +0.64. Weak support (2018-19 data quality).

## 2026-11-04: NFL home-pick spread CLV, followed up (pre-registered)
nfl-mixed-model `research/spreads/HOME_PICKS_PREREG.md` (f3278ee), results `HOME_PICKS_RESULTS.md` (a9aa3d4). Fable: no bugs.
- **Model information, not market drift:** model home-dog picks CLV +0.48 vs matched unpicked home dogs +0.01 (100th percentile of 5,000 draws). CLV rises with edge toward the home dog (-0.02 / +0.18 / +0.48).
- **Not a market pattern:** all home dogs 2011-19 (SBR open to close) CLV -0.27 [-0.37, -0.17].
- **Fresh weeks (2-4, 15-18):** model home-dog picks 96 bets, CLV +0.29 [+0.00, +0.56] vs break-even +0.61-0.64, -9.4u. **Test-only.** Home/away gap held (+0.27 vs +0.05). In-sample +0.44 shrank about a third.
- Home-dog CLV is mostly non-key-number half points (+0.33 vs +0.06 across 3/7). Use as a feature for the step-3 news model, not a bet.
- Data bug: SBR 2021-11-14 opening spreads have inverted signs (trusted rows); fix in clean_sbr.py.

## 2026-11-04: Spreads step 1 for NHL and NFL (honest baselines)
NHL (pre-registered nhl-mixed-model `research/spreads/STEP1_NHL_PREREG.md`, 1ab00db; results `research/spreads/STEP1_NHL_RESULTS.md`):
- Timing already honest (91.7% of DK openers post the day before before 7 PM; an extra night of results is worth nothing).
- v4 moneyline 1,267 bets +147.1u, CLV +0.23% [-0.07, +0.52]; v4 puck line 321 bets +35.6u, CLV +0.65% [+0.11, +1.19]. Keep both.
- Exploratory: ML CLV only in EV 9%+ (+2.22%; EV 4-9% -0.42% in every season despite +81.7u). Proposed ML bar 9% (not applied).
- Bug fixed live (NHL v4.1): -2.5 puck lines were priced/graded as -1.5.
NFL (pre-registered nfl-mixed-model `research/spreads/STEP1_NFL_PREREG.md`, 8eab781; results `research/spreads/STEP1_NFL_RESULTS.md`):
- Monday 9 AM spreads, weeks 5-14, edge 3+, 2020-25: 211 bets -6.9u, CLV +0.25 vs break-even +0.64. Stays test-only.

## 2026-11-04: PROVISIONAL bets tier (process) and NBA spreads v3.1
New standing rule (Jeffrey): ideas that look profitable but aren't proven are bet as PROVISIONAL with their own record and stop lines
fixed in advance, reviewed weekly (`research/PROVISIONAL_BETS.md`, `provisional_review.py`, daily in the morning run + health check).
First one: NBA spread injury-news bets (`PROVISIONAL_NEWS_SPREADS`, v3.1). Also corrected the spread record quoted in alert.py to the
honest step-1 numbers.

## 2026-11-04: NBA spreads, injury news after the opener (spreads plan step 3a)
Pre-registered (`research/spreads/STEP3A_NBA_INJURY_NEWS_PREREG.md`, d2813dc); results `research/spreads/STEP3A_NBA_RESULTS.md`.
- News bets (8 PM report creates a 3+ edge the opener model did not have): 10 PM line 61 bets 70.5% +21.1u, CLV +0.52 [+0.21, +0.85];
  7 AM line 75 bets 65.3% +18.5u, CLV +0.42. Below break-even CLV (+0.77): NOT passed. The same bets appear at 8 PM before the report.
- Waiting and betting all v2 at 10 PM: 304 bets +30.1u CLV +0.55 vs opener +3.8u CLV +0.84 on the same games: units and CLV disagree.

## 2026-11-04: NBA spreads v2 re-graded with opener-time information (spreads plan step 1)
Pre-registered (`research/spreads/STEP1_NBA_PREREG.md`, commit 022af82). `analysis/spreads_step1_nba.py` (output
`spreads_step1_nba_output.txt`); full write-up with takeaways `research/spreads/STEP1_NBA_RESULTS.md`. DK openers 2023-26, edge 3+.
- Original grading (8 PM report, lag 0) reproduces: v2 443 bets 58.9% +55.3u, CLV +1.16. Honest (previous report, lag 1): **466 bets
  54.1% +15.1u (+3.2/100, 90% -4.3 to +10.3), CLV +0.85 pts [+0.69, +1.01]** vs break-even +0.77. Oct-Jan part 373 bets +6.9u, CLV +0.82.
- The leak is the 8 PM injury report; the results lag is worth ~0. Bets only the 8 PM report creates: 88, 69.3%, +28.5u, CLV +1.72.
- Pre-registered verdict: survives (CLV at break-even, units positive), thin. Home dogs -36.8u honest; Pinnacle-cancelled bets -19.8u.
- Next: test the after-opener injury news at the line available when the report lands (spreads plan step 3).

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

## Second-half spreads by standings and roster changes (Nov 2, 2026)
`analysis/late_season.py` (output `late_season_output.txt`, bets `late_season_bets.csv`). Conference rank before each game:
top (1-4), middle (5-10), bubble (11-12 within 4 games of 10th), tanking (13-15 or further back). Recent arrival = a 12+ min
player who joined from another team in the last 30 days. Live spread model, DK openers, edge 3+, 2023-24..2025-26.
- Feb-Apr traps, negative all three seasons: betting a tanking team 239 bets 45.6% -30.9u; betting AGAINST a team in a playoff
  spot (5-10) 250 bets 41.6% -51.5u; tanking vs playoff-spot team 132 bets 40.2% -30.8u; our team with a recent arrival
  185 bets 43.2% -32.3u (new players valued at full EPM before they fit in).
- Feb-Apr excluding those three: 113 bets 60.2% +16.8u (+3.7, +3.0, +10.1); also no home dogs: 87 bets 63.2% +18.0u.
  The same exclusions don't matter Oct-Jan (traps +20.3u there). Found on the same seasons: paper-track before betting.
- Betting against a top-4 team in Feb-Apr: 155 bets 57.4% +14.9u (-6.2, +8.7, +12.4): top seeds rest late.
- Market (closing line, 2021-26 Feb-Apr): home bubble teams vs playoff-spot or top teams fail to cover by ~3 pts (4 of 5 seasons).

## Why totals at the CLOSE lost in 2024-25 (Nov 2, 2026)
`analysis/close_2025.py` (output `close_2025_output.txt`). At the opener the live totals model won every season (+46.3 / +40.3 /
+60.5u); at the close it was +6.5 / -52.8 / +8.3u.
- 2024-25 lines moved much more during the day: average total move open->close 3.19 pts (2.43-2.83 in other seasons), even in
  games with no late injury news (3.05 vs 2.27-2.65). The close improved on the opener by 0.52 pts of error (vs 0.33 and 0.27):
  that season the market (sharps) found and priced the information late.
- At the close, most "bets" are against a line that moved away from the model (415 bets, -38.9u in 2024-25) or exist only
  because the line moved away (close-only: 248 bets, -30.4u). Betting into a moved line = betting against the sharps.
- Same model, same season, at the opener: 479 bets, 56.8%, +40.3u. The close numbers are a stress test, not a strategy; the live
  rules already cover it (bet within the hour; PASS / DON'T BET once the line moves 0.5+ against).

## Feb-Apr spread traps on 12 older seasons (Nov 2, 2026)
`analysis/old_seasons.py`, `analysis/old_seasons_traps.py` (output `old_seasons_traps_output.txt`). 2009-10..2020-21 from the
2007-2024 closing-line dataset; Model 1 WITHOUT injury features (no injury reports or openers that far back), graded at the
CLOSING spread, so absolute results are weak (Feb-Apr 48.9%, -109u); what matters is the comparison:
- Betting tanking teams Feb-Apr 46.4% (-65.2u) vs Oct-Jan 53.4% (+6.5u): the tanking trap is real and late-season.
- Home underdogs lose in both halves (47.4% / 46.2%, positive in only 2-3 of 12 seasons): the home-dog rule is solid.
- Against playoff-spot teams: 49.1% Feb-Apr vs 49.2% Oct-Jan (not specifically a late-season effect in older seasons).
- Feb-Apr outside the traps and no home dogs: 379 bets 52.8% +2.8u (7 of 12 seasons positive) vs 48.9% for all Feb-Apr bets.

## NBA (and NFL) moneyline (Nov 2, 2026)
`analysis/nba_moneyline.py` (output `nba_moneyline_output.txt`). Win chance = logistic(model margin), fit leaving the season out;
DraftKings opening moneyline, 2023-24..2025-26, both teams 10+ games.
- Model accuracy is below DraftKings' opener (Brier 0.2055 vs 0.2007). Live spread model, EV 6%+: 1,814 bets +3.0u (-39.2 /
  +45.3 / -3.1). Base Model 1: -69.7u.
- With the spread rules (no home dogs; Feb-Apr outside traps): 861 bets +55.3u (+6.4%) but 2023-24 -11.9u (2 of 3 seasons).
  Favorites only +16.0u; Oct-Jan +41.2u (-20.6 / +38.0 / +23.8). It is the same signal as the spread bets, on the same games.
- Pinnacle's first moneyline against our side: 641 bets -82.6u (all three seasons negative); agrees/same +85.6u.
- Not adopted as BET alerts: not consistent enough, and it doubles exposure on games already bet on the spread.
- NFL moneyline (DraftKings openers 2020-24, early-week model): 775 bets -42.3u at EV 6%+; model less accurate than the opener
  (Brier 0.2264 vs 0.2172). No edge.
- Moneyline blend (model + DraftKings' opener, weight fit leaving the season out): the best weight on the model is only
  0.11-0.26, Brier 0.2005 vs 0.2007 for the opener alone; no bet threshold is consistent. The NBA moneyline opener already
  holds nearly everything the model knows. The -39/+45/-3 swings come from longshot underdogs (most bets +100 or longer):
  ~1,800 bets with big payouts give a season-to-season spread of about +/-35u, so with an average near zero the swings are noise.
- Across every market tested: the line moving our way after the bet = wins, against = losses; Pinnacle's first price against
  our side = losses (NBA spreads, NBA moneyline, NHL moneyline); the opener is about as accurate as our models overall, so
  the edge lives in specific disagreement spots (NBA totals, NHL moneyline/overs, NBA spreads Oct-Jan), not in every game.
- Moneyline takeaways (`analysis/nba_ml_takeaways.py`, output `nba_ml_takeaways_output.txt`), EV 6%+ at DK openers 2023-26:
  home moneylines lose every season (728 bets -42.7u): the model overrates home teams, the same bias behind the home-dog spread
  losses. Long shots (+200 or longer) carry the swings (-18.3 / +39.8 / -16.8). Away moneylines +150 or shorter: 460 bets
  +29.4u, positive all three seasons; with the live rules 313 bets +27.8u (+4.9 / +9.7 / +13.2), but half are games that already
  have a live spread bet; the new games add only +7.9u over three seasons (161 bets). Not adopted; paper-track candidate.

## Blending every model with DraftKings' opener (Nov 2, 2026)
`analysis/blend_all.py` (output `blend_all_output.txt`); NHL in nhl-mixed-model backtests/IDEA_TESTS.md. For spreads and totals
a blend (w x model + (1-w) x line) is the same as a bigger edge bar, so w (fit leaving the season out) says how much of the
model's disagreement to trust.
- NHL moneyline: blend adopted (55/45, EV 4%+): +158.1u, every season +19u or better.
- NBA totals: w = 0.49-0.52, i.e. the current edge-3 rule already IS the best blend (blended edge 1.5 = +163.1u vs +165.3u). No change.
- NBA spreads (live rules): w = 0.14-0.27 overall; blending removes nearly every bet. The live-rule bets at edge 3+ (442 bets
  59.5% +60.1u, every season positive) already filter to the spots where the model is right. No change.
- NBA moneyline: w = 0.11-0.26 (earlier test), no consistent bets. NFL: spreads w ~0 (-0.11 to +0.06), totals w = 0.14-0.32;
  the market already holds what the NFL model knows, consistent with full-game NFL staying test-only.
- NHL puck line and overs: blending removes the edge (puck line +12.0u vs +85.6u). Keep model-only.

## This season so far under the current rules (replay, Nov 2, 2026)
`analysis/season_replay_nba.py`; nhl-mixed-model `dev/season_replay.py`. Opening prices, locked picks (same information lag as live).
- NBA (88 games, Oct 20-31): totals v3 42 bets 19-23 -5.73u vs Model 1 alone 36 bets 18-18 -1.64u. Luck correction active in
  only 8 games (2-4 on its bets), altitude in 7 (1-4). Spreads: no bets yet (both teams need 10+ games).
- NHL (188 games, Oct 6 - Nov 1): 76 bets 41-35 +6.19u (+8.1%): moneyline (blend) 16 bets 9-7 +4.49u, puck line 35 bets
  17-18 -2.26u, overs 25 bets 15-10 +3.95u; old rules (plain model, both bets) 116 bets -8.15u. Pinnacle and second-chance
  rules can't be replayed (Pinnacle recording started Nov 2).
- Samples this small (one to four weeks) can't confirm or reject anything; the backtests remain the evidence.

## NFL retest with DraftKings openers through 2025-26 (Nov 2, 2026)
NFL 2024-26 odds downloaded (credits left ~204,000). Early-week model, edge 3+, opener, 2020-2025:
- Spreads: 462 bets 50.6% -15.3u (2024 -5.6, 2025 -4.5). Totals: 521 bets 53.7% +13.5u (2024 +9.2, 2025 -12.7).
- With fixes (each fit leaving the season out): totals + wind/cold + week 15+ shrink 438 bets 55.7% +27.8u (2 of 6 seasons
  negative: 2021 -5.4, 2025 -6.5); spreads + week 15+ shrink 362 bets 53.6% +8.4u (3 of 6 negative). QB and home fixes don't help.
- Moneyline (1,725 games): model Brier 0.2250 vs DraftKings opener 0.2159; EV 6%+ 944 bets -63.2u (4 of 6 seasons negative).
- Second-half totals can't be checked at real openers: the odds history has full-game markets only.
- Verdict unchanged: full-game NFL stays test-only; weather + late-season tracking continues live this season.

## NFL: player-based strength and the totals-with-weather autopsy (Nov 2, 2026)
Scripts: analysis/nfl_player_model.py, analysis/nfl_totals_autopsy.py (bets: nfl_totals_autopsy_bets.csv, output: nfl_totals_autopsy_out.txt).
Player features: nfl-mixed-model nfl_player.py / dev/player_features.py (nflverse play-by-play 2017-2026). For each team: expected starting
QB's EPA/dropback (career, recency-weighted, shrunk), rushing EPA, pass/rush EPA allowed, pace, QB-change flag. Walk-forward, DK openers 2020-25.
Fixed: 37 games had two DK opener rows (duplicates) in earlier NFL scripts; deduped here (the weather totals rule is +29.8u, not +17.8u).

**Spreads: the player model does not help.** Alone: 968 bets, 50.3%, -38.3u (MAE 10.84 vs the opener's 9.93). Added to the team model: -9.9u.
Added to the opener: no edge. The NFL spread market already prices QBs and matchups better than box-score EPA can.

**Totals: the player model is a useful second opinion.** Alone +22.5u (598 bets). Unbiased in 2026 (mean error +0.2 pts).

Weather totals autopsy (436 bets, 56.0%, +29.8u):
- Weeks 1-4 lose: -13.4u (lost in 2021, 2024, 2025; also lost for the player model and the plain team model, and in 2026: weeks 1-4 -2.5u to -3.3u).
  From week 5: 310 bets, 59.7%, +43.2u, worst season -0.4u. Reason: early in the season the models still run on last year's teams.
- Unders +25.0u vs overs +4.8u; unders at outdoor stadiums +18.3u; unders with wind 11+ mph 60.6%.
- Divisional games +20.8u (positive every season) vs +9.0u non-divisional.
- Opening total 46-49: -17.9u (43.0%); totals 40 or under and 49+ were the best. Not used (no clear reason, could be noise).
- Line moved our way by the close: +38.3u; moved against us: -8.2u (the existing 0.5-pt "against" caution covers this live).
- 46-60 F outdoor +26.6u every season (mostly the weeks 5-14 effect). Grass vs turf, rest, pace, kickoff slot: nothing consistent.
- Player model agrees (weeks 5+): 216 bets, 61.1%, +36.0u, positive all 6 seasons; disagrees: 94 bets, +7.2u.

**Adopted (test-only, live switch TOTALS_LIVE in alert.py):** total = average of (team + weather model) and (player model + its own weather),
bet at 2+ pts of edge, weeks 5-14 only. 2020-25: 375 bets, 58.4%, +43.1u, every season positive (+0.7 to +13.2u). (The first write-up
said 475 bets / +44.3u; that count wrongly included weeks 15+, which added 100 bets and about +1u.) 2026 weeks 5-8 (true out of
sample, ESPN openers): 20-12, +6.2u. Caveat: the week-5 cutoff was picked after looking; it held for three separate models and in 2026.

### Follow-up (Nov 2, 2026): totals v2 switched LIVE; QB model diagnostics; v2 wins vs losses
Scripts: analysis/nfl_qb_diagnostics.py, analysis/nfl_totals_v2_autopsy.py (output nfl_totals_v2_autopsy_out.txt).
**Bug found:** the spread version of the player model had the defense sign backwards (EPA allowed was subtracted instead of added).
Totals were not affected (the totals sum was correct). Fixed: player spread model MAE 10.94 -> 10.28 (team model 10.21, opener 9.93),
but it still loses at the opener (-12.2u alone; -4.4u added to the team model). Conclusion unchanged: no spread edge.
Why QB stats don't beat the spread:
- QB EPA per dropback repeats only 0.44 season to season (CPOE 0.36, team passing 0.41, point margin 0.42): about half of a season's
  QB efficiency is noise (tipped interceptions, fumble luck, drops, opponents).
- 1 SD of QB passing edge = 1.8 pts of margin; recent point margin = 2.8 pts. The QB is one input of several.
- The starter differs from last game's in 13.7% of team-games; using the actual starter (known by kickoff) barely helps
  (MAE 10.33 -> 10.29) and bets were worse: the market prices QB news within minutes.
- Longer memory, opponent adjustment, CPOE, special teams, team passing instead of QB: none beat the opener.
v2 autopsy (375 bets): unders 61.7% +31.2u (all six seasons positive) vs overs 55.5% +11.9u; overs at outdoor stadiums -1.0u;
unders in close games (spread 6.5 or less) 64.6% +29.5u; unders in wind 10+ mph 64.0%; cold (40 F or below) 41.9% -6.2u (unders 37%);
overs on 47.5+ totals 48.4%; both models past the line 67.4%; line moved against us by close 50.0%.
Stronger signs (both models past the line, or an under in wind 10+ / a close game, with no weaker sign): 141 bets, 66.7%, +38.5u.
Weaker signs (over outdoors, 40 F or colder, over on 47.5+): 122 bets, 47.5%, -11.3u. In 2026 weeks 5-8 the weaker group went 4-1,
so it is shown as a note in the alerts, not a rule. Revisit at season end.

## 2026-11-03: how much weight does the model deserve versus the market line? (NBA, 2024-25 + 2025-26, 2,448 games)
Script `analysis/market_shrink_test.py`, output `analysis/market_shrink_test_output.txt`. Regression of (actual - line-implied) on (model - line-implied):
the slope is the weight the model's disagreement deserves (1 = trust it fully, 0 = the line already has everything).
- Against OPENING lines: spreads 0.25 (+/-0.09; 0.29 in 2024-25, 0.20 in 2025-26), totals 0.39 (+/-0.10; 0.36 and 0.44).
- Against CLOSING lines: spreads -0.06 (+/-0.08), totals -0.13 (+/-0.09): nothing left once the market has finished moving.
- Takeaway: the model has real but small information at the opener, and an "edge of 3 points" is worth about 0.75 points of true edge on spreads
  (about 1.2 on totals). That fits the flat win-rate-by-edge result above and the market-moved-against-us result. It is the case for betting only
  at the opener and for shrinking the number toward the line (NFL's late-season shrink is the same idea). Same weights in both seasons, but it is
  one fit on two seasons: treat 0.25 / 0.39 as a first estimate, re-test on 2026-27 live data, and add "Model 1 shrunk" as a side-by-side
  record rather than changing Model 1.

## 2026-11-03: Model 1 on nine older seasons at SBR OPENING lines (job 4, research/HANDOFF_TO_OPUS.md)
`analysis/old_seasons_sbr.py` (output `old_seasons_sbr_output.txt`, bets `old_seasons_sbr_bets.csv`). 2013-14..2021-22, SportsbookReview
openers and closers (consensus lines, -110 assumed), Model 1 **without injury features** (no reports that far back), one-day lag,
trained on up to 4 earlier seasons. Data fixes: SBR dates the 2020 bubble games a year early (159 rows); playoffs dropped; checks pass
(82 games per team; Charlotte 7-59 in 2011-12 confirms the Hornets/Pelicans names).
| Edge 3+, trusted rows | At the opener | At the close |
|---|---|---|
| Spreads | 2,456 bets 49.8% -123.1u (positive 2 of 9 seasons) | 50.1% -132.6u |
| Totals | 4,311 bets 52.8% **+34.1u** (positive 4 of 9) | 49.5% -271.4u |
- Weight on Model 1 vs the opener: spreads 0.13 (+/-0.04), totals **0.11** (+/-0.05); vs the close 0.06 / -0.12.
  Compare 2023-26 at DraftKings openers with injuries: 0.15 / 0.32.
- Untuned shrunk rule (weight from the other seasons, bet when it beats -110): spreads 50.1% -23.5u; totals 177 bets 55.9% +12.0u.
- Accuracy (mean absolute error): margin Model 1 9.98 vs opener 9.74 vs close 9.67; total 14.49 vs 14.30 vs 14.04.
- Takeaway: the team-ratings part of Model 1 has only a thin totals edge at the opener over ten years (+0.8% per bet, a weight of 0.11)
  and none on spreads. The much stronger 2023-26 totals result comes with things this test lacks: injury reports at the open, the luck
  and form terms, and DraftKings' own (softer?) openers rather than SBR's consensus. Finding out which of those carries the edge is the
  first job of the model tournament.

## Rule audit: timing look-ahead and gates (Nov 4, 2026)
Full write-up: research/RULE_AUDIT_2026-11-04.md (all three repos). NBA totals: 74% of DK openers post before the 8 PM report the
backtest paired them with; betting the opener with the info already out was +109.3u (1,565 bets, 56.0%) vs +126.7u backtested,
while the live gate (wait for the report, push only lines moved toward the model) captures ~+17.5u. Unmoved lines with 3+ edge win
at every check time (9 PM 56.7%, +54.5u), contradicting the "unmoved for hours ~49%" OPTIONAL rule. PASS-on-against holds at night.
NFL: backtest opener is ~6.7 days before the early number exists; Tuesday 10 AM line +11.6u vs live final-report rule +3.5u.
NHL: Pinnacle follow-up and moneyline b2b skip are ~break-even under the live blend; puck line 6-9% EV band -11.1u.

## Statistics concept catalog: 98 course methods applied to NBA totals v4 (Nov 4, 2026)
Full catalog, scripts and per-game data: [`research/stats_catalog/`](../research/stats_catalog/README.md). v4 at DraftKings openers 2023-26,
1,446 bets at edge 3+ (56.7%, +119.5u); out-of-sample checks on 9,591 SBR-opener games 2011-19.
- v4 edges are ~55% real: (final - opener) on edge slope 0.55. Logistic map edge -> P(win): 3 pts 53.7%, 6 pts 57.4% (calibrated). Use it for EV/Kelly.
- Line moving our way by close: win 61.2% vs 48.1% when it moves against (odds ratio 1.70, CI 1.37-2.11).
- Random-side permutation test p = 0.0002; same-night results independent; no streaks (runs p = 0.96).
- Power: ~2,300 bets for 80% power to detect a true 55%; one season's ROI is ~1.9 SE from zero.
- Replicates 2011-19: miss size grows with the total (rank by edge/SD to test next); totals right-skewed (mean > median); "over teams" regress to 50%.
- April runs over the opener (2023-26 +3.4, 2011-19 +1.45) but only ~51% of April games go over: tail, not a lean. January under didn't replicate.
- Warning: altitude over (+4.3 vs opener 2023-26; +2.8 vs close 2021-26) was absent 2011-19 (-0.5). Keep v4's +3.8 but watch it first if totals slip.
- No gain: edge size buckets, over vs under, rest, edge x early-season, polynomial edge terms. v4 is no more accurate than the opener in absolute error; profit is direction at the open.

## Edge relative to noise (Nov 4, 2026, follow-up to the statistics catalog)
`research/stats_catalog/edge_sd_test.py`, rule written before running. Noise model fit on SBR 2011-19: mean miss 13.8 pts at a 200 total,
15.0 at 240. Ranking bets by edge / noise instead of raw edge picks 1,440 of the same 1,446 bets in 2023-26 (+119.5u either way; logistic AIC
4400.2 vs 4400.5) and, on Model 1's 2013-22 SBR bets, the top halves by each measure both win 53.5%. Verdict: keep raw edge; the noise gradient
is real but too small to matter for bet selection.

## Line moved against the model: keep the PASS rule (Nov 4, 2026)
`analysis/LINE_MOVE_RESULTS.md` (pre-registered in `analysis/LINE_MOVE_PREREG.md`). Out of sample (SBR 2013-22) win rate at the opener falls
with the size of the move against: totals 53.6% (0.5) -> 49.3% (1) -> 46.4% (1.5) -> 42.2% (2-2.5) -> 37.4% (3+); toward 58.0%. Early moves
(first 90 min) are no better than later ones; 46% of early against-moves swing back by the close but betting them still lost. DraftKings has
posted only half-point lines since Oct 2025, so live moves are whole points. Totals "1 pt against" was +20.6u on DK 2023-26 but -6.4u at the
SBR close: no change, tracked in the new shadow record (`shadow_passed.py`, `state/shadow_passed.md`).

## Bail-out after the line moves against a placed bet (Nov 4, 2026)
`analysis/BAILOUT_RESULTS.md`. DK 2023-26 opener bets: totals still win ~50% after a 1-2 pt move against but 45% at 3+ and 39.5% at 4+;
spreads drop to 45% after 1 pt and 33% after 2. Live as a PROVISIONAL alert (`bailout.py`): cash out only above the break-even
(totals 3+: 86% of stake; 4+: 76%; spreads 1+: 86%; 2+: 64%), otherwise ride.

## Hedges and middles: no system (Nov 4, 2026)
`analysis/MIDDLES_RESULTS.md`. Middling our own bets after a move toward the model loses (other side wins 44-48%, every season). Book-gap
middles at DK + FD lose at every gap after removing bad quotes; across 5 US books totals 2.5+ gaps made a thin +1.1u per 100 pairs; only
offshore books show real middle value. Revisit after moving out of CT.
