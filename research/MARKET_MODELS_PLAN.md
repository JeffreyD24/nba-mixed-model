# Market models project: outcome, opener, movement, blend

Started Nov 5, 2026. Pilot: **NBA full-game totals**. If it works, the same four-part setup is copied to NBA spreads,
then NHL/NFL, then NCAA and derivative markets (quarters, halves, props), and possibly other markets (Polymarket, stocks).
Status lives at the bottom of this file. Linked from `JeffreyD24/betting-goals` GOALS.md.

## Why four models instead of one
Each model answers a different question, so they are combined by job, not averaged.

| # | Model | Question it answers | Target | What it is used for |
|---|---|---|---|---|
| 1 | Outcome (fair value) | What will actually happen? | final total points | Our own number. Already exists: totals v4 and the stack. Never sees any line, so it can disagree with the market. |
| 2 | Opener | How does each book build its opening number? | first line seen, per book (DraftKings, FanDuel, Pinnacle) | Goal "figure out how bookmakers create opening lines". The **residual** (actual opener minus what the book's usual process predicts) flags likely opener mistakes worth betting fast. |
| 3 | Movement | Where will the line go from here? | close minus current line, at each snapshot | Bet-now-or-wait timing, and a direct forecast of CLV (our primary measure). Predicting the move beats predicting the close level, because the current line already carries most of the information. |
| 4 | Blend | What is our best estimate of the true number? | final total points | Weighted mix of model 1 and the market (Pinnacle line), weights fit on past seasons. The weights say honestly how much our model adds beyond the market. |

**Bet rule to test (pre-registered before looking at results):** bet when the blended fair value vs the best DraftKings/FanDuel
line clears the edge threshold, and the movement model does not expect the line to come to us. If it expects movement toward
us, wait (bail-out and timing logic already exist to reuse).

## Ground rules
- **No leakage.** The opener model only uses information known when lines opened; the movement model only what was known at that snapshot. Every feature gets an "available at" time.
- **Same train/test seasons across sports when possible** (standing preference). Train 2021-22 to 2024-25, test 2025-26, then live 2026-27 as the forward test.
- **CLV first, units second, accuracy alongside.** Remember CLV comparisons across bet times favor earlier bets.
- **Write the rule down before testing.** New pieces go in as PROVISIONAL until proven. Fable double-checks before anything goes live.
- Every model part gets a one-line note on what it does (second standing goal).

## Step plan
1. ~~Data audit: which books and seasons have opening and closing totals~~ (done Nov 5, below)
2. ~~Opener model for DraftKings and Pinnacle totals~~ (done Nov 5: residual predicts movement, not results; pre-registered bet failed, see `research/market_models/STEP2_OPENER_RESULTS.md`). Was: (features: prior totals, team pace and efficiency, rest, travel, injuries known at open, previous opener errors)
3. ~~Movement model~~ (done Nov 5: CLV +1.52 vs break-even +1.07 on 2025-26 but -8.7u, so fails the written rule; shadow record proposed; see `research/market_models/STEP3_MOVEMENT_RESULTS.md`). Was: (features: line gap between books at that moment, time to tip, betting splits, injury news since open, our model's edge)
4. Blend on 2021-22 to 2024-25, tested on 2025-26
5. Pre-register the combined bet rule, backtest, then run it as a side-by-side record next to v4 in 2026-27
6. If it beats v4 on CLV: copy the setup to NBA spreads, then NHL and NFL

## Step 1 results: data audit (Nov 5, 2026)
**Source:** `data/odds_history/nba/` (The Odds API historical snapshots), 10 books including Pinnacle, DraftKings and FanDuel.

| Season | Games per book | Median snapshots per game | Gap between snapshots | DraftKings first seen (median hours before tip) | Pinnacle first seen |
|---|---|---|---|---|---|
| 2021-22 | ~1,240 | 30 | 1 h | 20.8 | 10.3 |
| 2022-23 | ~1,230 | 32 | 50 min | 21.2 | 13.7 |
| 2023-24 | ~1,231 | 41 | 30 min | 26.8 | 13.2 |
| 2024-25 | ~1,235 | 42 | 30 min | 25.6 | 19.7 |
| 2025-26 | ~1,228 | 40.5 | 20 min | 24.2 | 21.2 |

- Closing lines: the last snapshot is within about 5 minutes of tip for 99%+ of games for every book (2021-22 lowvig 75% is the exception).
- 6,161 games have both a Pinnacle and a DraftKings total from first seen to close.
- Also available: SBR archive 2011-12 to 2021-22 (consensus open and close, no per-book lines) and live 2026-27 snapshots every 5 minutes from Pinnacle plus 9 US books (`research/live_odds/nba/`, since Nov 2) and Action Network open/DraftKings/FanDuel (`research/books/`).

**Limits to keep in mind**
- "Opener" here means **first line seen**, not the true opener. Snapshots were hourly in 2021-22, so the first DraftKings number can be up to an hour old news. The live tracker now catches true openers within 5 minutes; that is the cleaner target going forward.
- Pinnacle shows up later than DraftKings in the archive (median 10-21 h before tip vs 21-27 h). Pinnacle's first-seen line is therefore partly a later line, not a fair "opener vs opener" comparison.

## Personal note and takeaways
- **We have what we need for the pilot.** Five full seasons of per-book open-to-close totals, including Pinnacle, is enough to train opener and movement models on four seasons and test on the fifth.
- **First finding, and a trap.** Looking at first-seen lines, DraftKings moved toward Pinnacle's number in 78.5% of games where they started 1+ point apart. That looks like "Pinnacle leads." But when both books are compared **at the same snapshot time**, it drops to 55% toward Pinnacle vs 34% away, and Pinnacle moved toward DraftKings almost as often (53%). Pinnacle's same-time line only barely predicts DraftKings' close better than DraftKings' own line (2.10 vs 2.12 points average miss). Most of the 78% was a timing artifact: Pinnacle's first line was seen later, closer to the close. Same lesson as the CLV timing bias: compare lines at the same moment or the result is fake.
- **What that means for the plan.** Pinnacle is not a magic leading signal for totals by itself. The movement model needs to combine several inputs (book gaps, splits, injury news, time to tip) rather than lean on one.
- **Next:** build the DraftKings and Pinnacle opener models on 2021-22 to 2024-25, test on 2025-26.

## Status log
- 2026-11-05: plan written; step 1 data audit done (see above). Next: step 2, opener models.
- 2026-11-05: step 2 done. Mixed opener model predicts DK/Pinnacle/FanDuel first-seen totals within 2.4-2.5 pts (2025-26). Pre-registered residual bet failed (2025-26: 381 bets, CLV +1.00 vs break-even +1.07, -18.5u; 2024-25 was +2.12 CLV, +33u). Residual predicts line movement in both seasons, so it becomes a step-3 input. Next: step 3, movement model, same-moment book comparisons.
- 2026-11-05: step 3 done. Boosted movement model (same-snapshot book gaps, price leans, move so far, step-2 opener residual) on 2025-26: 573 bets, CLV +1.52 (break-even +1.07), -8.7u, 51.8% (expected 53.3%). Fails the rule on units; CLV check shows 1 pt CLV = +2.2% wins in NBA totals, close is fair. Next: step 4, blend; shadow record for the movement rule.
- 2026-11-05: price CLV (juice skew, closed). Pinnacle's no-vig closing price adds information beyond its number (T1 pass both seasons), DK's does not. Movement rule 2025-26 re-graded: +2.06% EV vs DK close, +1.90% vs Pinnacle (break-even 0%); residual rule break-even. No verdict changed. See `research/market_models/PRICE_CLV_RESULTS.md`.
- 2026-11-05: step 4 done (blend passes: honest timing 257 bets, CLV +1.44, +1.8u vs v4 +0.79). Movement (v1-an, Action Network books, honest timing 385 bets CLV +1.31, -10.8u) and blend live as PROVISIONAL with money from 4:52 PM ET (market_models_live.py), Fable-checked twice. Next: step 6, copy to NBA spreads, then NHL/NFL, with the reachability filter from day one.
