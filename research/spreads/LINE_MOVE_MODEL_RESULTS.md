# NBA line-move model — results (Nov 4, 2026)

Pre-registration: `LINE_MOVE_MODEL_PREREG.md` (commit 0c3dd9e; script 9008e13, both pushed before any result).
Output: `analysis/line_move_model_output.txt`. Exploratory timing table: `analysis/line_move_timing_explore_output.txt`.

## Verdict: FAIL for both spreads and totals. By the time we can act on the game-day report, DraftKings has already priced it.

5,106 games (2021-26) with an 8 PM night-before report, a game-day pretip report and DK lines throughout.
News = injury value on the pretip report minus the 8 PM report, in points.

| | Spreads | Totals |
|---|---|---|
| Full open-to-close move per point of news (build) | 0.75 | 0.88 |
| Move still to come after the act line, per point of news | **0.04** | **0.11** |
| Momentum (does an earlier move continue?) | none (-0.003) | none (-0.013) |
| Break-even CLV at -110 (build) | +1.28 pts | +0.33 pts |
| Bets at theta 0.5+ (build / test) | 0 / 0 | 7 / 1 |

The predicted remaining move almost never reaches half a point, so the pre-registered rule makes no bets (spreads none; totals 1 test bet).

Data limit worth knowing: DK history has ~hourly snapshots at fixed clock minutes, so "first line at or after slot + 15 min" landed a
median **56 min** after the report slot, not 15. Live we check every 5 min, so this test is a late read. It does not change the picture
much: 73-76% of the news is already in the line *before* the slot.

**Absorption, games with 1.5+ pts of news** (share of the full move): before the report slot 73% spreads / 76% totals, at the act line
83% / 97%, close 91% / 100%.

## Exploratory (after results): when during the day does the news get priced?
Share of the eventual move in DK's line by ET clock time (games with 1.5+ pts of news; spreads / totals):

| 10 PM night before | 7 AM | 10 AM | noon | 2 PM | 4 PM | 6 PM | close |
|---|---|---|---|---|---|---|---|
| 1% / 11% | 5% / 9% | 7% / 11% | 14% / 18% | 31% / 35% | 51% / 53% | 65% / 65% | 88% / 87% |

(means; medians are 0% through 10 AM, then 33-36% at 2 PM and ~50-65% at 4 PM). Caveat: the news is defined by the final pretip
report, which nobody knew at noon, so this shows when the *market* learned, not a bettable rule.

## Personal note and takeaways
- **The pretip report is old news.** By the time it posts (~5-6 PM for most games), about three quarters of what it says is in the line,
  and the rest is gone within the hour. Building a bet on that report is chasing.
- **The news arrives between noon and 6 PM.** Before noon almost nothing has moved; by 6 PM two thirds has. That window is when the
  earlier game-day reports post (11 AM, 1, 3, 5 PM), plus shootaround and reporter news. If there's a catchable edge, it's a status change
  on the 11 AM / 1 PM / 3 PM report read within minutes, which is exactly what Part A (live timing) measures.
- **No momentum to ride.** Once the line has moved, the earlier move does not keep going (coefficients ~0).
- Totals price news slightly more completely than spreads (100% vs 91% by the close), and have a much lower break-even CLV (+0.33 vs +1.28
  at the act line), so if a news edge exists anywhere it's more likely in totals.
- Next step (proposed): backfill every game-day report slot for 2021-26 through GitHub Actions (`backtest_v2/download_injury_reports.py`
  already fetches 11 AM-9 PM; nba.com is reachable from Actions, not from this workspace), parse each slot, and re-run this test per slot.
  That is the historical version of Part A, with hundreds of times more events than the live log has today.
- Nothing live changes.
- Carry-over to other markets: scheduled public disclosures (like an earnings release) are priced before the formal release when the same
  information leaks through earlier channels; the formal release itself is rarely the moment to trade.
