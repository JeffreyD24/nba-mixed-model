# Step 3 results: movement model for DraftKings NBA totals (Nov 5, 2026)

Pre-registration: `STEP3_MOVEMENT_PREREG.md` (committed fd8a220 before fitting).
Code: `movement_model.py`, `clv_conversion_check.py` (exploratory). Outputs: `movement_results.json`,
`movement_bets_2025_26.csv` (every pre-registered test bet).

## Verdict
**Fails the written rule, but only on units, and the CLV is well above break-even.**

| Bet DK the first time the predicted move is 1.5+ pts | Bets | CLV (pts) | Break-even | Units | Win % |
|---|---|---|---|---|---|
| 2024-25 (validation, exploratory) | 662 | +2.11 ± 0.15 | +1.07 | +42.3 | 55.8% |
| **2025-26 (pre-registered test)** | 573 | **+1.52 ± 0.13** | +1.07 | **-8.7** | 51.8% |

The rule needed CLV above +1.07 **and** positive units. CLV passed by about 3.5 standard errors; units did not.
At +1.52 CLV the expected win rate is 53.3% (about +10 units on 573 bets). The actual 51.8% is 0.7 standard
deviations below that: ordinary bad luck, not evidence the CLV is fake (see the check below). Still, the rule was written
in advance and it says fail, so **nothing is bet**. Recommendation: a **shadow record** (logged, graded, no alerts,
no money) through 2026-27, with the live 5-minute snapshots and betting splits added.

Exploratory: threshold 2.0 pts gave 303 bets, CLV +1.87, +10.8u in 2025-26; 1.0 pts gave 1,015 bets, CLV +1.10, -1.0u.
Only betting 3 h+ before tip changed nothing (almost all bets fire 12-30 h out; median 23 h).

## The model
Boosted trees beat ridge in validation (weighted MSE 7.61 vs 7.75; predicting "no move" 8.33) and on the test
(5.85 vs 5.89; no move 6.27). It removes **6.7%** of the error in "where will DK close vs now" on 2025-26. That sounds small,
but most line movement is news nobody can see coming; the bets only fire on the predictable part.

**What predicts DraftKings' next move** (ridge weights, standardized, bigger = more pull):
| Input | Weight | What it means |
|---|---|---|
| Opener residual (step 2) | -0.31 | DK opened off its usual formula -> the line comes back. The strongest single input. |
| FanDuel - DK gap now | +0.25 | DK moves toward FanDuel's number. |
| Other books' median - DK now | +0.22 | DK moves toward the rest of the market. |
| Move so far | +0.21 | Momentum: a line that has started moving keeps moving the same way. |
| Opener model - DK now | +0.17 | DK drifts toward the formula's number. |
| Pinnacle price lean | +0.16 | When Pinnacle juices the over (or under) before moving the number, DK's total follows. |
| Pinnacle - DK gap now | +0.07 | Small once the other gaps are in: Pinnacle alone is not the leader (same as step 1). |
| DK price lean, hours to tip, books quoting | ~0 | Little extra. |

## Check: does CLV really turn into wins in NBA totals? (exploratory, after seeing the result)
Two steps in a row had positive CLV and negative units, so I checked whether a point of CLV is worth what the break-even
assumes. Hindsight bets on every game 2021-26 (side the DK line later moved toward, at DK's first-seen total), 5,643 games:

| CLV | Games | Won | Expected if the close is fair |
|---|---|---|---|
| 0-1 pt | 1,394 | 51.9% | 51.8% |
| 1-2 | 1,255 | 55.7% | 54.0% |
| 2-3 | 989 | 58.3% | 56.1% |
| 3-5 | 1,245 | 59.8% | 59.2% |
| 5+ | 760 | 66.1% | 65.4% |

Win rate rises **2.2% per point of CLV**, exactly the fair-close assumption, and it holds every season (2025-26: 57.3% vs 56.6%
expected). So the DK close is a fair number, CLV is worth what we think, and the +1.07 break-even is right.
The 2025-26 movement bets just ran cold.

## Exploratory: adding our own model's opinion
Model 3 (pace x efficiency, opener-time report) is only available for 2024-25 and 2025-26, so this is fit on 2024-25 and tested
on 2025-26. Its edge vs the current DK line got a large weight (+0.85) but barely changed accuracy (MSE 5.96 vs 5.96). Bets:
489, CLV +1.83, +20.2u, 54.8%. Encouraging for step 4 (the blend), but one season, not pre-registered.

## Personal note and takeaways
- **This is the closest we've come to "beating the close" on purpose.** A model that only reads the market at one moment
  (book gaps, price leans, how far the line has moved, and where the opener formula says it should be) finds bets that
  beat DK's close by 1.5 points on a season it never saw. That clears break-even by a wide margin.
- **The CLV check matters for every model we have.** In NBA totals, 1 point of CLV = 2.2% more wins, and the close is fair.
  So CLV is the right first measure (as the standing rule says), and small samples of units can mislead in both directions.
- **Why not bet it now:** it failed the rule we wrote. One season of positive CLV and negative units isn't enough to override
  that. A shadow record in 2026-27 settles it, with better data: 5-minute snapshots instead of 20-60 minutes, and splits.
- **What changes in how we think:** the opener residual is the strongest input, so the step 2 work wasn't wasted. And Pinnacle
  matters through its *price* (juice) more than its number.

## Next
- Step 4: blend (our outcome model + market + movement prediction), the exploratory result above suggests the pieces add.
- Shadow record for this movement rule in 2026-27 (needs the live snapshot version and a Fable check before it runs).

## Addendum (Nov 5, 2026, afternoon): live version without Pinnacle ("movement v1-an")
Jeffrey asked for the movement bets to go live with money as PROVISIONAL. The Odds API live feed (Pinnacle + 9 books) paused that
morning when the plan's credits ran low (the player-prop backfill used them), so the live model can only use the free Action Network
feed: DraftKings, FanDuel, Caesars, BetMGM, BetRivers (no Pinnacle). Pre-registered as an addendum (7f40f5e) before running,
same fit/test/trigger, refit without the night-before injury report and without the Pinnacle inputs:

| v1-an, bet the first 1.5+ predicted move | Bets | CLV | Units | Win % |
|---|---|---|---|---|
| 2025-26 test | 505 | **+1.41 ± 0.15** | **+5.4** | 53.3% |
| 2024-25 | 710 | +1.83 | +71.2 | |

It passes both parts of the original rule (CLV above +1.07 and units positive), better on units than the Pinnacle version
(593 bets, CLV +1.47, -8.0u), so Pinnacle's inputs weren't carrying the result. Live since Nov 5 (research/PROVISIONAL_BETS.md).
Bets with fewer than 3 books quoting (DK posts first) were 187 of the 505, CLV +1.42: no reason to wait for other books.

## Correction (Nov 5, 2026, Fable check): bets the live code can actually make
The team features are keyed by game date, so a snapshot taken before a team's previous game was played still used that game's
box score. Live, the code waits until the morning run after both teams' previous games (box scores arrive ~11:41 AM ET).
144 of the 505 v1-an test bets fired before that point. Re-run with only reachable snapshots (and 48 h or less before tip), trained
the same way (`export_movement_model.py --an --reach`, live model `data/movement_model_v1an_reach.json`):

| v1-an, reachable snapshots only | Bets | CLV | Units | Win % |
|---|---|---|---|---|
| 2025-26 test | 385 | **+1.31 ± 0.16** | **-10.8** | 51.2% |
| 2024-25 | 519 | +1.59 | +19.4 | |

CLV still clears break-even (+1.07), by about 1.5 standard errors; units do not. The addendum's live bar was CLV, and Jeffrey asked
for these to go live with money as PROVISIONAL, so it does, with its stop lines. Honest expectation: about +0.5% per bet from the
CLV, which the vig and luck can easily swamp. This is the weakest of the live provisional rules.
