# NCAAM Model 3: result / DraftKings opener / DraftKings close targets. Results (Nov 5, 2026)

Pre-registration `ncaab/research/MODEL3_PREREG_2026-11-05.md` (+ addendum for MKT-T). Code `ncaab/model3.py`, `model3_mktt.py`, `model3_grade*.py`.
Outputs `model3_output_run1.txt` (first run), `model3_output_mktt.txt` (tuned market model), `model3_output_mktl.txt` (one-day lag), `model3_spread_diagnostics.txt`.

## Three targets (DraftKings 2023-24 + 2025-26, spreads)
| Target | Best | Error (pts) | Books |
|---|---|---|---|
| A: game result | blends with the opener | 11.25 | DK opener 11.25, DK close 11.19 (the close is still the most accurate predictor) |
| B: DK opener | BLEND-B (M2 + M8 + tuned market model) | 2.06 | - |
| C: DK close | BLEND-C (+ opener) | 1.48 (move R^2 +0.09) | opener alone 1.55 |
Totals: same picture (opener predicted to ~3.0 pts; close move R^2 +0.12).

## The rule that passed: stale-line spreads
MKT-T = the team model fitted to market-implied points from past closing lines (ridge 0.2, tuned on 2009-11 openers). BLEND-C predicts the
close from the opener and the models; bet DraftKings' opener when it is 0.5+ pts off the predicted close (in practice: the opener sits ~4-6 pts
from the market's own ratings, and ~13% of that gap closes by tip).
- First run (MKT untuned): no pass. Tuned: **DK 709 bets 57.0% +61.5u CLV +1.26** -> PASS. One-day lag: 642 bets 57.8% +65.5u CLV +1.29 (DK decision rows; note the lagged variant would NOT have passed the pre-registered SBR threshold step, CLV +0.59 < 0.63; only the unlagged MKT-T did).
- **Fable review: APPROVE WITH FIXES.** Corrected headline (ESPN DK opener and close, pre-game filters only): **623 bets 57.9%, +65.5u (+10.5%),
  CLV +1.27**; 2023-24 +24.6u, 2025-26 +40.8u; Nov-Dec 62%, Jan-Feb 56-57%, March 53%. At real DK prices +58.7u.
  Other books' (later) openers in the same feed: flat (CLV +0.57-0.79): the edge is in DraftKings' FIRST number and decays within minutes.
- Fable also found: ~2.4% of Action Network-ESPN game links pair the wrong games (score-pair matching): to fix before trusting other college CLV records.
- Totals: CLV above break-even (+1.17) but -46.7u at DK: FAIL.

## Live (PROVISIONAL, Nov 5, 2026; live code reviewed by Fable: APPROVE WITH FIXES, all must-fix and should-fix items applied)
`ncaab/live_alert.py` in the 5-minute alert loop records DraftKings' first college spread (Action Network feed, timestamped) and alerts when fresh
and 0.5+ off the predicted close; `ncaab/live_ratings.py` (morning) builds lagged ratings; `ncaab/live_grade.py` grades vs our own DK close.
Stops: -15u; at 100 bets stop if CLV < +0.63 or units < 0. Expect ~6-7 alerts a day once teams have 3+ games (about a week from now).
