# Spreads step 3a (NBA): injury news after the opener — results (Nov 4, 2026)

Pre-registration `research/spreads/STEP3A_NBA_INJURY_NEWS_PREREG.md` (commit d2813dc, pushed first). Script
`analysis/spreads_step3a_nba.py`, output `analysis/spreads_step3a_nba_output.txt`. DraftKings 2023-26, games whose night-before report
is the 8/9 PM snapshot (2,634 of 3,204). Break-even CLV +0.77 pts (90% +0.64 to +0.98).

| Bets (C model = 8 PM report) | Line | Bets | Win % | Units | Per 100 [90%] | CLV [90%] |
|---|---|---|---|---|---|---|
| **N news bets (PRIMARY)** | **T1 10 PM** | **61** | **70.5%** | **+21.1** | [+15.4, +50.1] | **+0.52** [+0.21, +0.85] |
| N news bets | T2 7 AM game day | 75 | 65.3% | +18.5 | [+6.7, +40.3] | +0.42 [+0.15, +0.69] |
| N news bets (diagnostic) | T0 8 PM, before report | 55 | 70.9% | +19.5 | [+14.5, +56.2] | +0.61 |
| W all v2 at the line | T1 10 PM | 304 | 57.6% | +30.1 | [+1.1, +18.8] | +0.55 [+0.40, +0.70] |
| W all v2 at the line | T2 7 AM | 308 | 56.5% | +24.2 | [-1.0, +16.9] | +0.40 |
| B v2 at the opener (step 1, same games) | opener | 378 | 52.9% | +3.8 | | +0.84 |

News bets by season (T1): +0.9 / +10.5 / +9.7u; (T2): +4.5 / +6.4 / +7.7u.

## Verdict (pre-registered rule)
**Not passed.** The rule required CLV at or above break-even at T1; news bets reached +0.52 (interval +0.21 to +0.85). Units are strongly
positive, so the result sits in the goals.md cell "units up, CLV short of paying the vig" = likely luck until more bets say otherwise.
The pre-registered rule had no explicit row for "CLV positive but below break-even, units positive"; reading it with the goals.md
table is the conservative choice.

## What the numbers say
- **The report itself barely moves the DraftKings line.** The same news bets already show up at 8 PM, before the report (T0), with
  the same record. So this is not "the market is slow to price the 8 PM report"; the news bets are games where the model with the
  updated injury list disagrees with a line that has drifted the other way (lines moved ~1 pt AWAY from these bets since the open).
- **70% on 61 bets with only +0.5 pts of CLV doesn't add up**: CLV that size predicts ~52% (50% + 3.1 pts per point x 0.52). Either luck, or the model knows something
  the close also misses (game-day scratches priced late). 61 bets cannot tell these apart.
- **Waiting for the report and betting all v2 at 10 PM / 7 AM made more units than the opener on the same games** (+30.1u and +24.2u vs
  +3.8u) but with lower CLV (+0.55 / +0.40 vs +0.84). Units and CLV disagree; CLV comparisons across timings favor the earlier bet
  (noted earlier), so neither "wait" nor "bet the opener" is shown better.

## Takeaways
1. **Don't build a news-bet alert yet.** The win rate is eye-catching but CLV says it isn't paying the vig on a reliable basis; 61 bets
   over three seasons is too few.
2. **The live season is the cleanest test.** `research/injury_decisions.csv` logs each status change with the line at that moment, and
   per-minute lines exist since Nov 3. Recommend recording N-type news bets as a TEST bucket this season (no push) and checking CLV at
   ~100 bets. Needs approval.
3. The 7 AM line still carries most of the effect (T2 close to T1), so if it becomes real, it fits Jeffrey's schedule without overnight bets.
4. NHL and NFL spreads step 1 (honest baselines) have **not been started yet**.
