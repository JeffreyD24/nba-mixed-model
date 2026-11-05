# NCAA men's basketball Model 1: results (Nov 5, 2026)

Pre-registration: `ncaab/research/NCAAM_PREREG_2026-11-05.md` (pushed before any result). Output: `ncaab/research/backtest_output.txt`.
Data: 28,975 D-I games 2021-22 to now (`ncaab/data/games.csv`); Open / DraftKings / FanDuel lines from 2023-24 (about 4,800 eligible games a season).

## Model
Ridge mixed model of team points (offense + opponent defense + home court; neutral sites from ESPN), refit every game day, walk-forward.
Tuned on 2022-23 results only (no lines): ridge 5, carryover 0.8 of last season's rating, no recency decay (`ncaab/research/tune_2022_23.csv`).
Accuracy 2022-23: margin RMSE 11.5 vs the consensus close 11.1 (a sensible first model; the market is still better).

## Pre-registered result: both markets FAIL -> test-only this season
| Market | Threshold (chosen on 2023-24) | Test bets 2024-26 | CLV vs break-even | At the Open | At the DK close |
|---|---|---|---|---|---|
| Spreads | 5+ pts | 448 | +0.95 [+0.71, +1.24] vs 0.67 | 233-214, 52.1%, -2.2u | -31.8u (-7.1%) |
| Totals | 6+ pts | 914 | +1.09 [+0.90, +1.27] vs 0.99 | 476-438, 52.1%, -5.3u | -47.8u (-5.2%) |
Fails on the units part of the rule (units at the Open must be > 0). No alerts; `ncaab/daily.py` (workflow `ncaab.yml`, 9:17 AM ET)
grades the same rule on 2026-27 as a TEST record (`ncaab/state/test_record.md`), in the daily health check.

## What it means
- **CLV well above break-even but no profit:** the Open book is a soft first number that moves toward the sharp close no matter
  who bets it. Beating it by ~1 pt is the norm, not proof of edge. At the DraftKings close the model loses 5-7% (= the vig):
  it knows nothing the closing line doesn't. For NCAAM, "CLV vs the Open" overstates edge; judge future versions at DK's own lines.
- 85% of spread test bets are Nov-Dec, when the model and market disagree most (ratings still forming). The model is weakest
  exactly where it bets most.

## Descriptive only (not tested; candidates for Model 2 pre-registration)
- Totals in **conference games**: 580 bets 55.9%, +38.5u at the Open and **+14.6u at the DK close**, both test seasons positive.
- Totals Jan-Apr: 54.8%, +25.8u at the Open, flat at the close. Totals Nov-Dec: 47.7%, -31.1u.
- Spreads at **neutral sites**: 65 bets 64.6%, +15.2u (small).
- Model 2 ideas: possessions (tempo x efficiency, like the NBA pace x efficiency model) instead of raw points; early-season prior from
  returning minutes / transfers; regulation-only totals (OT inflates).

## Takeaways
1. College basketball's opener is not as soft as hoped against a plain team-rating model; the market prices team strength well.
2. The conference-game totals pattern is the one lead worth a written-in-advance test on a new season of data.
3. The data pipe (free, 5 seasons, DK + FD) is the durable win: it feeds Model 2 and the women's game (same source) next.
