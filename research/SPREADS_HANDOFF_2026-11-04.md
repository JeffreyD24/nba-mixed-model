# Handoff: evaluate and tune the spread models (NBA spreads, NFL spreads, NHL puck line / moneyline) — Nov 4, 2026

For a new session. Goal set by Jeffrey: evaluate the spread-type models in all three sports and fine-tune them so they become profitable.
Read first: `claude/goals.md` (how we judge a model), `claude/findings_log.md` (newest first), `claude/leakage_audit_2026-11-03.md`,
`claude/rule_audit_2026-11-04.md`. Same file in all three repos: `research/SPREADS_HANDOFF_2026-11-04.md`.

## Honest starting point
Every spread test so far says **team ratings alone do not beat the opening spread**. Tuning a model that has no information the line
lacks only finds noise that looks good on the tuning seasons. So "fine-tuning" here means: find information the opener does not have yet
(or uses badly), prove it on unseen seasons, and only then tune thresholds. A valid outcome for a market is "not beatable with what we
have"; say so plainly if that is what the data show.

| Sport / market | Best evidence so far | Status |
|---|---|---|
| **NBA spreads** | Model 1 at DK openers 2023-26 (lag-fixed): 1,226 bets 50.8% -36.6u. Shrink weight vs opener 0.15 (a "3-pt edge" is ~0.5 pt). Tournament 2018-22: no candidate beat the opener (stack +0.24 MSE, 13% chance negative); fragile: dropping CHI/NO 2014-18 makes it squeak past (+0.31 [+0.00, +0.63]). "Missed last game" injuries add nothing. Earlier: Model 2 (lineups x player ratings) had the most accurate margins. | **Live v2** with filters: BET Oct-Jan once both teams have 10+ games, never home underdogs (confirmed on 12 older seasons: home dogs 46-47%); Feb-Apr traps (tanking confirmed, playoff-spot trap NOT); PASS when Pinnacle's first spread disagrees (timing problem: Pinnacle posts 5-12 h later). The Oct-Jan record (+42u, 355 bets) was graded with the 8 PM report at openers that mostly post 2-7 PM: **re-test with opener-time information before trusting it.** |
| **NFL spreads** | DK openers 2023-25: 103-104, 49.8%. SBR openers 2016-19 (never seen): 238 bets 46.6%, -11% (interval -21% to -1%); model MAE 10.19 vs opener 9.88; shrink weight 0.06. QB-quality, EPA, blend, player model: all lose. Tuesday line (rule audit): -3.2u. Mid-week injury news since the early number: spreads 272 bets 54.8% +12.5u (CLV +0.12), not shown; **QB part +1.52 [+0.05, +2.99]** (exploratory hint). News priced by the close: QB ~75%, WR/TE/RB/LB only 20-35%. | **Test-only.** Most promising angle: injury/practice news (non-QB positions) acted on before the line moves; the live injury logger (`research/injury_log`) and Wayback ESPN injury captures 2022-25 now exist to test it. |
| **NHL puck line / moneyline** | Moneyline: shot model + expected goalie on SBR holdout 2017-22: CLV +0.23 win-% pts better than no goalie, log loss 0.6677 vs opener 0.6668; no ML rule confirmed (best +1.7%/bet, -2% to +6%). Fitted market weight 0.30-0.40 (live blend uses 0.55). Model's underdog leans deserve less weight (0.23-0.33 vs 0.41-0.68 favorites). Long shots (+150 and longer) are the weak spot. Puck line at close: -1.5%. Rule audit (2021-26, bettable prices): puck line 6-9% EV band 514 bets -11.1u (negative 4/5 seasons), 9%+ +90.2u (chosen in-sample); one-bet-per-game picks the wrong leg (dropped ML legs +57.3u). | **Live v3.1** (ML blend EV 4%+, puck line EV 6%+). Rule-audit changes proposed, not applied. |

## Rules for this session (from goals.md and the audits; do not skip)
1. **Pre-register every test** (push the rules to GitHub before any result). CLV is the primary measure, units the second check,
   accuracy reported alongside. Read them together with the table in goals.md.
2. **Timing:** the model may use only information known when the graded line was posted. Know each sport's opener time:
   NBA DK openers ~24 h before tip (mostly 2-7 PM the day before; use the one-day lag); NHL ~31 h before (results through two days
   before); NFL DK totals/spreads post ~9-12 days ahead, so grade at the line posted when the model could actually run (Monday 9 AM is
   now the live NFL lock, totals v4).
3. **Seasons:** build / choose / lockbox splits. Tune only on build seasons, pick on choose seasons, open the lockbox once. Prefer the
   same split across sports where data allow (Jeffrey's preference). Seasons the live rule was chosen on cannot confirm it.
4. **Units at real prices:** -110 for NBA/NFL spreads unless real prices exist; NHL at the actual moneyline / puck-line price. Compare
   price-terms CLV with about -4.5%, not 0.
5. **Nothing live changes without Jeffrey's approval**; an approved change is a new version row in `state/bet_versions.csv` and a
   new entry in `config/thresholds.csv`.
6. Write a findings-log entry and a repo note (GitHub) for every result, with a takeaways section.

## Suggested plan (in order; each step pre-registered)
1. **Inventory and honest baselines (all three).** Re-grade each live spread rule at a bettable time with opener-time information
   (NBA spreads v2 Oct-Jan record and Feb-Apr traps; NHL puck line and moneyline v3.1; NFL spreads at Monday 9 AM). Report accuracy,
   CLV and units per season. This tells us where we really stand.
2. **Shrink-to-line framing everywhere.** Fit the weight w in `line + w x (model - line)` on build seasons; bet when the shrunk number
   beats the price. Spreads weights are near 0 (NBA 0.15, NFL 0.06): if a new feature cannot raise w on unseen seasons, it does not help.
3. **Information the opener lacks (the only realistic source of a spread edge):**
   - NBA: injury and rest decisions after the opener (`research/injury_decisions.csv` logs status changes with the line at that moment;
     `state/injury_reports_2026_27.csv` keeps every official report); Model 2 lineups with the expected rotation; back-to-back rest.
   - NFL: practice reports Wed-Fri, non-QB positions (priced only 20-35% by the close), the QB hint from the mid-week test; data:
     nflverse injuries 2009-26 (final snapshots; use the prior week for early lines), Wayback ESPN captures 2022-25, live injury log.
   - NHL: confirmed starting goalie before the line reacts (biggest measured gain), skater lineup news (Bluesky reporters, Daily
     Faceoff); data: `research/goalies.csv`, goalie tables 2010-23 (hockeyR and official box scores, 99.96% agreement).
4. **Calibration / market weight (NHL especially):** separate weights for favorites and underdogs, long-shot handling, and which leg
   (moneyline vs puck line) to bet; check against the rule-audit proposals.
5. **Only then tune thresholds** (edge size, EV bar) on build seasons, confirm on the lockbox, and propose live changes with the
   expected numbers (accuracy, CLV, units).

## Data and code pointers
- Odds: DraftKings + Pinnacle + 8 books, The Odds API snapshots (NBA/NHL 2021-26 hourly-ish, NFL 2020-26 ~3-hourly) in
  nba-mixed-model `data/odds_history/`; SBR openers/closers (NHL 2011-22 in nhl-mixed-model `data/external/sbr/`, NBA used in the
  tournament 2014-22, NFL 2011-21); live per-minute pregame and in-game lines since Nov 3 (`research/pregame/`, `research/live/`).
- NBA: `nba_mixed_model.py` (Model 1), Models 2/3, `research/tournament/` (tournament code and preregs), `analysis/lag_leak_test.py`
  (one-day lag), `analysis/shrink_weights.py`, `data/external/nba_box/` (player-games + missed_value 2013-26; CHI/NO 2013-18 empty).
- NFL: `nfl_mixed_model.py`, `backtest.py`, `dev/` tests (SBR opener, midweek injury, player features), nba-mixed-model
  `analysis/nfl_timing_team.py` (team model re-solved at any cutoff time; reuse it for spreads), `data/external/nflverse_injuries/`,
  `data/external/injury_history/espn_wayback/`.
- NHL: `nhl_xg_model.py` (shot model), `nhl_mixed_model.py` (goals model, alerts stopped), `dev/oos_sbr_*.py`, goalie recal test
  (`backtests/GOALIE_RECAL_PREREG.md`), `analysis/rule_audit_nhl.py` (needs rebuilt `box_hist.csv` / `shots_hist.csv`, gitignored).
- Per-rule bootstrap, calibration, Pinnacle CLV: `edge_stats.py` in each repo (`research/edge_stats/REPORT.md`).

## Process notes
- Bots commit every 5 minutes: pull --rebase before every push (retry loop). Dispatch workflows via REST
  (`gh api -X POST repos/OWNER/REPO/actions/workflows/NAME.yml/dispatches -f ref=main`).
- The workspace reaches GitHub only; ESPN, nhle.com, Open-Meteo, archive.org and IEM are reached through GitHub Actions workflows.
- Jeffrey's preferences: findings on GitHub as well as in Project docs, a takeaways section in every result, phone pushes only for bets,
  every new data feed added to the daily health check.
