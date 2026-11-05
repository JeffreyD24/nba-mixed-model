# College model tournament: results (Nov 5, 2026)

Pre-registration `ncaab/research/TOURNAMENT_PREREG_2026-11-05.md` (pushed first). Code `ncaab/tournament.py`; outputs
`ncaab/research/tournament_output.txt` and nfl-mixed-model `ncaaf/research/tournament_output.txt`.
Entrants: M1 Model 1, M2 moving scoring level, M3 regulation-only (basketball), M4 multiplicative (log points), M5 all combined, M6 average.

## Winners: none passes. Both sports stay TEST records.
| Sport / market | Winner (highest CLV) | Bets | CLV (break-even) | At the Open | At the DK close | Every season + at Open |
|---|---|---|---|---|---|---|
| NCAAF spreads | **M1** | 1,056 | +1.16 (0.92) | **+43.3u** (23: +14.3, 24: +19.0, 25: +10.0) | -2.6% | yes |
| NCAAF totals | M6 average | 1,125 | +1.55 (0.94) | +28.2u | -6.1% | yes |
| NCAAM spreads | M5 everything | 667 | +0.92 (0.67) | +9.0u | -3.0% | no (25-26 -4.5u) |
| NCAAM totals | M5 everything | 619 | +1.44 (0.99) | +1.5u | -5.9% | no |

## What each idea did
- **Moving scoring level (M2):** removes the drift that inflated NCAAM totals: 6+ totals bets fell from 1,155 to 793 and CLV rose
  +1.11 -> +1.23, but still no profit (-6.3u at the Open). It fixes the bias that killed the conference-totals pattern; it does
  not create an edge. (No effect on spreads, as expected: the level cancels in a margin.)
- **Multiplicative (M4):** the best single change for NCAAM (spreads +3.5u, totals +3.4u at the Open, best DK-close numbers); hurts NCAAF.
- **Regulation-only (M3):** no help.
- **Everything (M5):** best NCAAM model on both markets, still loses at the close and in 2025-26.
- **NCAAF spreads: plain Model 1 is already the best.** Nothing beat it.

## Decision
No model goes live. NCAAM daily TEST record stays on Model 1 (the TEST rule is fixed for the season); M5 predictions are kept in
`ncaab/data/tourn_preds.csv` for a written-in-advance 2026-27 comparison. NCAAF spreads remain the strongest college candidate:
the question is only whether DraftKings' own first line is as soft as the Open book (being recorded from Nov 5).
