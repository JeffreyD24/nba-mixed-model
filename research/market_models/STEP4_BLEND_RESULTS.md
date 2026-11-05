# Step 4 results: blend of v4 + market + expected move, NBA totals (Nov 5, 2026)

Pre-registration: `STEP4_BLEND_PREREG.md` (committed c0f08c4 before fitting). Code: `blend_model.py`.
Outputs: `blend_results.json`, `blend_bets_2025_26.csv` (every pre-registered test bet), live weights `data/blend_v1.json`.

## Verdict: passes
| At the first DK line after 9 PM the night before | Bets | CLV (pts) | Break-even | Units | Win % |
|---|---|---|---|---|---|
| **Blend, edge 2+ (pre-registered test, 2025-26)** | 314 | **+1.79 ± 0.17** | +1.07 | **+23.3** | 56.4% |
| Baseline: v4 alone, edge 2.5+ (same games, same moment) | 594 | +1.13 ± 0.12 | +1.07 | +39.8 | 55.9% |
| Movement model alone, 1.5+ (same moment) | 167 | +1.53 | +1.07 | -9.3 | 49.7% |
| Blend, 2024-25 (fit season, exploratory) | 301 | +2.06 | +1.07 | +18.8 | 55.7% |

All three conditions in the rule hold: CLV above break-even, units positive, and more CLV per bet than v4 alone. So the blend
goes live as a **PROVISIONAL** rule (labeled, own record, stop lines), after the Fable check.

v4 alone still made more total units in 2025-26 (+39.8u on 594 bets vs +23.3u on 314). The blend's case is quality per bet
(+1.79 vs +1.13 CLV, on a measure where 1 pt = 2.2% more wins). Its bets are mostly v4's best ones, filtered by the market.
So it runs **next to** v4, not instead of it. When both fire on the same game and side, the alert isn't sent twice.

## The weights (what each part is worth)
Fair total = -22.2 + **0.38 × v4** + **0.72 × (DK now + expected move)**, fit on 2023-24 and 2024-25.
- The market (DK's line plus where it's expected to close) carries about two thirds of the weight, v4 about one third.
  Our model adds real information beyond the market, but the market is the better half.
- The weights add to 1.10, so the blend stretches totals away from the league average slightly. That's why **80% of bets are
  overs** (252 of 314). Both sides cleared break-even on CLV: overs +1.89 (57.5% wins), unders +1.36 (51.6%).
- Without the expected move (v4 + DK now only): 260 bets, CLV +1.42, +30.1u. The movement piece raises CLV per bet
  (+1.79) but trims bets and units: it moves the blend's number toward where DK will close, so some v4 edges disappear.
- Live weights (`data/blend_v1.json`) are refit on all three seasons: -17.4 + 0.38 × v4 + 0.70 × (DK now + expected move).

## Exploratory (not part of the decision)
- **At DK's first-seen line** (often before the 8 PM report, so v4 is partly ahead of what was known): blend 536 bets, CLV +1.72,
  +59.0u; v4 alone 596 bets, CLV +1.49, +49.0u. Both look better at the opener, as the live v4 rule already assumes.
- Edge 1.5: 471 bets, CLV +1.36, +40.0u. Edge 3.0: 132 bets, CLV +2.07, -4.4u (small sample).
- Accuracy on the final total (mean absolute error, 2025-26): blend 14.79, v4 14.80, DK at 9 PM 14.84, DK close 14.60.
  Nothing beats the close on accuracy; the edge is in **which** games, not in a better number on every game.

## Caveats
- v4's add-ons (luck, form, altitude) were chosen on 2023-26, so v4 is partly in-sample in both the blend and the baseline.
  Only the 2026-27 live record is fully clean.
- One test season (314 bets). The provisional stop lines (research/PROVISIONAL_BETS.md) handle the risk.
- Decision moment is fixed: one look per game, at the first check at or after 9 PM ET the night before (or when DK first posts).

## Personal note and takeaways
- **This is the first market-models piece that passes its written rule outright.** Four steps in, the pattern is clear:
  our model alone is about break-even on CLV, the market alone is the benchmark, and the edge is in **combining** them,
  betting only where our model and the market's own expected move agree that DK is off.
- **It answers "how much is our model worth?" with a number:** about 0.38 of a point per point of disagreement, once the
  market is in. That's the honest size of v4's information, and a target to beat with every model improvement.
- **Watch the over lean.** If scoring falls league-wide, an 80%-overs rule would get hit together. The weekly provisional
  review shows overs and unders separately so this is visible early.

## Next
- Live as PROVISIONAL (alerts with money), next to v4 and the movement rule.
- Step 5 of the plan (pre-register the combined rule and run side by side) is effectively this; step 6 (copy to NBA spreads,
  NHL, NFL) is next once there's a few weeks of live record.

## Correction (Nov 5, 2026, Fable check): honest decision timing
The 9 PM night-before decision could use a box score from a game played that same night (a team on a back-to-back). Re-run with the
decision at the first DK snapshot at or after 9 PM **and** after the morning run following both teams' previous games
(`blend_model.py` now uses `--reach`; results `blend_results_reach.json`, bets `blend_bets_2025_26_reach.csv`; the first run's files
are kept as `blend_results.json` / `blend_bets_2025_26.csv`):

| Honest timing, 2025-26 | Bets | CLV | Units | Win % |
|---|---|---|---|---|
| **Blend, edge 2+ (pre-registered rule)** | 257 | **+1.44 ± 0.18** | **+1.8** | 52.9% |
| v4 alone, edge 2.5+ (same moment) | 598 | +0.79 ± 0.11 | +18.4 | 54.0% |
| Blend, edge 1.5 (exploratory) | 390 | +1.25 | +21.3 | 55.4% |
| Blend, 2024-25 (exploratory) | 231 | +1.39 | +17.1 | 56.3% |

It still passes all three conditions (CLV above +1.07, units positive, more CLV per bet than v4 at the same moment), but the units are
now thin (+1.8u) and **89% of bets are overs** (228 of 257). Weights: -17.9 + 0.31 × v4 + 0.77 × (DK now + expected move); live weights
refit on 2023-26: -14.0 + 0.31 × v4 + 0.76 × market (`data/blend_v1_reach.json`). The "first run" numbers above (314 bets, +1.79,
+23.3u) are superseded.

Also worth noting: v4 itself at this later, honest moment has CLV +0.79, below break-even. v4's value is at the opener, which is where
the live v4 rule bets. The blend is the way to use v4's opinion later in the day.
