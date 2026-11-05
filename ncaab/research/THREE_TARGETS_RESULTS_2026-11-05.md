# NCAAM three-target tournament: results (Nov 5, 2026)

Pre-registration `ncaab/research/THREE_TARGETS_PREREG_2026-11-05.md`. Code `ncaab/three_targets_preds.py`, `ncaab/three_targets_grade.py`;
output `ncaab/research/three_targets_output.txt`. Fit = DraftKings rows 2023-24 (4,659 games), TEST = DraftKings rows 2025-26 (4,472), ESPN BET 2024-25 secondary.
New entrant **MKT** = team ratings fitted to past games' closing lines (how the market rates each team). **ENS** = blend of M2, M8, MKT fit on 2023-24.

## A. Predicting results (RMSE, lower = better; TEST 2025-26)
| | M1 | M2 | M8 | MKT | ENS | DK opener | DK close |
|---|---|---|---|---|---|---|---|
| Spreads | 11.60 | 11.60 | 11.55 | 11.67 | **11.47** | 11.27 | 11.22 |
| Totals | 17.33 | 17.30 | 17.35 | 17.57 | **17.24** | 17.18 | 16.96 |
ENS (M2 + MKT, M8 adds nothing) is our most accurate model; DraftKings' opener and close are still better.

## B. Predicting DraftKings' opener (RMSE vs the opener, TEST 2025-26)
Spreads: M2 2.72, M8 2.55, MKT 3.32, **blend 2.36** (0.43 MKT + 0.56 M2). Totals: M2 3.28, M8 4.10, MKT 5.07, **blend 3.10** (0.84 M2 + 0.14 MKT).
Results-based ratings predict the opener better than market ratings do: DraftKings' opener looks like a results-based power rating.

## C. Predicting the close from DraftKings' opener (TEST 2025-26)
| | C0 (close = opener) | C1 + M2 gap | C2 + MKT gap | C3 + M8 gap | C4 + group terms |
|---|---|---|---|---|---|
| Spreads RMSE (corr with actual move) | 1.532 | 1.523 (+0.16) | 1.488 (+0.27) | 1.487 (+0.26) | 1.485 (+0.26) |
| Totals RMSE (corr) | 2.670 | 2.651 (+0.15) | **2.490 (+0.36)** | 2.492 (+0.36) | 2.517 (+0.34) |
Line moves are partly predictable out of sample. The strongest single term is MKT minus the opener: DraftKings' line moves toward how the market
has been rating the teams. Group terms (C4) help a little in-sample, not out of sample.

## Betting the predicted move (bet DK's opener in the predicted direction when |predicted move| >= k; k chosen on 2023-24)
- **Spreads (k 0.5): 797 bets 52.6%, CLV +0.65 [90% low +0.53] vs break-even 0.63, +2.9u at the opener, -18.1u at the close.** Passes the
  written rule by 0.02 pts of CLV. Decision (Claude, standing permission): **held as a TEST record, not sent for PROVISIONAL**: expected ROI is
  about zero and every bet spends DraftKings account life. Jeffrey can override (Fable review first).
- **Totals (k 0.5): 2,633 bets 51.7%, CLV +1.10 vs 1.02, -34.7u at the opener. FAIL.**

## Takeaways
1. We can forecast part of DraftKings' line move (corr +0.26 / +0.36): the first college CLV-forecasting tool. Useful for timing even without
   its own bets (e.g. bet a model-edge game early when the close model also predicts a move our way; wait when it predicts against).
2. DraftKings' opener is closer to a results-based rating than to the market's consensus rating; the move afterwards is toward the consensus.
3. Next models: combine the close model with the results-model edge (bet only where both agree), and add information the opener lacks
   (injuries / lineups, travel), the only way past the close.
