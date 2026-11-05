# CLV in price terms: results (closes the "juice skew" idea, plans/2026-11-05.md idea 2)

Pre-registration: `PRICE_CLV_PREREG.md` (commit ab9bc59, pushed before any result).
Code: `price_clv_build.py` (per-game first-seen and close, DK and Pinnacle, line and both prices from the same snapshot),
`price_clv.py` (tests). Outputs: `price_lines.csv.gz`, `price_clv_results.json`, `price_clv_movement_bets.csv`.

## Verdict
**Closed.** The price matters a little, and only Pinnacle's: its closing price adds information beyond its closing number
(T1 passes for Pinnacle, fails for DraftKings). Re-grading in price terms changes **no verdict**. The step 3 movement rule
still beats the close (+2.1% EV) and the step 2 residual rule is still break-even. The live version already exists:
`edge_stats.py` grades every live bet against Pinnacle's no-vig closing price since Nov 3 (`research/edge_stats/REPORT.md`).
Nothing new to build, no rule changed.

## Slope: points per unit of probability (fitted on 2021-22 to 2023-24 only)
| Market | Win-rate change per point of line | k (points per 1.00 of probability) |
|---|---|---|
| Totals | 2.47% | 40.5 |
| Spreads | 3.44% | 29.1 |

So -120/+100 on a total (no-vig 52.4% vs 50%) is worth about 1 point of line. Same order as the step 3 check (2.2% per
point at DraftKings' close).

## T1: does the closing price carry information beyond the closing point? (2024-25 and 2025-26, never used to fit)
Brier score gain of using the no-vig closing price over a flat 50% at the closing line (x1000; higher is better; 90% range).

| Book | Market | 2024-25 | 2025-26 | Pass (both > 0)? |
|---|---|---|---|---|
| Pinnacle | Totals | +0.58 [+0.15, +0.97] | +0.35 [-0.12, +0.79] | **Pass** |
| Pinnacle | Spreads | +0.44 [+0.02, +0.84] | +0.36 [-0.10, +0.81] | **Pass** |
| DraftKings | Totals | -0.12 [-0.34, +0.11] | +0.39 [+0.07, +0.73] | Fail |
| DraftKings | Spreads | +0.21 [-0.09, +0.49] | -0.07 [-0.59, +0.40] | Fail |

The effect is small: closing prices lean only 0.1-0.3 points' worth on average. But Pinnacle's lean points the right way
every season, DraftKings' doesn't. Per the pre-registration, price CLV against **Pinnacle's** close is reported
alongside point CLV (which `edge_stats.py` already does).

## T2: does DraftKings' first-seen price lean predict DraftKings' move? (2025-26, descriptive)
| Market | Games | Correlation | Slope (points moved per point of lean) |
|---|---|---|---|
| Totals | 1,224 | +0.10 | +2.2 |
| Spreads | 1,224 | +0.19 | +1.9 |

On its own, yes: a juiced over at the open tends to be followed by a higher total, and the move is about twice the size the
price implies. Step 3 found DK's lean adds about nothing **once the gaps to other books are in the model**, so the lean is
mostly the same information as "other books are already higher." Not a new signal; already captured by the movement model.

## T3: re-grades in price terms (break-even is 0% EV)
| Bets | n | Avg price | Point CLV | EV, point only (close at -110) | EV vs DK no-vig close | EV vs Pinnacle no-vig close | Units |
|---|---|---|---|---|---|---|---|
| Step 3 movement rule, 2025-26 | 573 | -111.3 | +1.52 | +2.61% | **+2.06% (se 0.62)** | **+1.90% (se 0.62)** | -8.7 |
| Step 2 residual rule, 2025-26 | 381 | -110.2 | +1.00 | +0.17% | +0.02% (se 0.81) | -0.06% (se 0.81) | -18.5 |
| Live 2026-27 picks | 0 | | | | | | |

- Price trims about half a percent off the movement rule's edge (the closing price leaned toward our side a bit), but it
  stays about 3 standard errors above break-even. Verdict unchanged: CLV passes, units failed, shadow record recommended.
- The residual rule is break-even in every view, matching its point CLV of +1.00 vs the +1.07 break-even.
- Live picks: none could be graded here. The 5-minute recorder started Nov 2 at 5:42 AM, after the Nov 2 picks were locked,
  and later games aren't graded yet. `edge_stats.py` covers live bets from now on.

## Takeaways
- **Use Pinnacle's no-vig close as the price reference; don't bother pricing DraftKings' close.** Pinnacle's lean carries
  information, DraftKings' doesn't.
- **Price adjustments are small for NBA sides and totals** (about 0.1-0.3 points on average), so point CLV is a fair
  shortcut for NBA; price CLV matters more where lines rarely move in points (NHL totals, moneylines).
- **No verdict flipped.** Closing this item; the checklist line "CLV in PRICE terms against Pinnacle's de-vigged close" is done.
