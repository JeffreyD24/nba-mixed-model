# NBA model tournament: pre-registration (written Nov 3, 2026, before any tournament result)

Question: **what, if anything, beats DraftKings'/the market's opening line?** Committed before results; git history is the proof.
Code: `research/tournament/nba_tournament.py`. Results go to `research/tournament/NBA_RESULTS.md`.

## Rules for every candidate
- Walk-forward with the **one-day lag** (results through two nights before the game; research/LEAKAGE_AUDIT_2026-11-03.md).
- Only information known at the opener. No closing lines as inputs.
- Each candidate is turned into a market-anchored number: `line + w x (candidate - line)`, with `w` fit (OLS through the origin)
  on the BUILD seasons only. The opener alone is the baseline (w = 0).
- Regular season only. Games where both teams have 10+ games this season (early-season numbers are mostly last year).

## Seasons (END-year labels)
| Split | Seasons | Lines | Use |
|---|---|---|---|
| BUILD | 2014-2018 | SBR openers (trusted rows) | fit weights and stack coefficients |
| CHOOSE | 2019-2022 | SBR openers (trusted rows) | compare candidates, pick ONE per market |
| LOCKBOX | 2023-2026 | DraftKings openers (The Odds API) | score the picked candidate ONCE, refit on 2014-2022 first |
Caveat set now: 2023-26 were used to develop the live luck/form/altitude rules, so the lockbox favors those incumbents.
The truly clean forward test is 2026-27 (live). SBR openers are a consensus line; DraftKings' may be softer.

## Tier A candidates (box scores only, available 2012-2026)
1. **Opener** (baseline).
2. **Elo**, published FiveThirtyEight NBA settings, NOT tuned: K = 20, margin multiplier ((MOV+3)^0.8 / (7.5 + 0.006 x elo diff)),
   home edge 100 Elo, 25% carry-back to 1505 between seasons, 28 Elo points = 1 point of spread. Totals: no Elo; uses #3's totals part.
3. **Simple averages**: season-to-date point margin (spreads) and season-to-date points for + against (totals), home edge from the
   build seasons. The simplest possible rating.
4. **Model 1** (REML mixed model, no injury features), as in analysis/old_seasons_sbr.py.
5. **Model 1 + last-10 form** (form weight 0.20 totals / 0.11 spreads as live; recomputed with the lag).
6. **Stack**: OLS of (result - opener) on [Model 1 - opener, Elo - opener (spreads), simple - opener, form, altitude flag (DEN/UTA
   home, totals), both-teams-rested flag], fit on BUILD. Features fixed here; no feature selection on CHOOSE.

## Tier B (2022-2026 only: injury reports, shots) - measured, not lockboxed
Injury features (night-before report), shooting luck. Only DraftKings seasons exist, all already studied, so these are scored by
leave-one-season-out as the contribution to the Tier A pick. Labeled "already-seen seasons". Box-score "missed last game"
proxies back to 2012 would move injuries into Tier A: data job for later (GitHub Actions can reach the NBA stats API).

## Scoring
- **Primary:** reduction in mean squared error of the anchored number vs the opener alone (ΔMSE, points²), with a 90% interval from
  a paired bootstrap that resamples whole game-days (2,000 draws). Also the share of draws below zero.
- **Secondary:** untuned bets (anchored number beats -110: |anchored edge| >= 0.0597 x sd of build-season misses): count, win %,
  units at -110, and **CLV in points** (closing line minus opener, in the bet's direction).
- Every candidate is reported on BUILD (in-sample, for reference), CHOOSE, and, for the pick only, LOCKBOX.

## Decision rules (set now)
- On CHOOSE, a candidate **beats the opener** only if ΔMSE > 0 with the 90% interval above zero AND its bets' average CLV > 0.
- Pick per market: the candidate with the largest CHOOSE ΔMSE among those that pass; if a simpler candidate is within the other's
  interval, pick the simpler one (order of simplicity: 3 < 2 < 4 < 5 < 6). If none pass, the answer for that market is "nothing
  beats the opener", and no lockbox run is done for it.
- LOCKBOX is run once per market for the pick. Its verdict uses the same pass rule. No changes after it is opened.
- Nothing live changes without the user's approval; a promoted candidate gets its own record (new version = new record).
