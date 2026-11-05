# NBA quarter / half / team-total lines — results (Nov 4, 2026)

Pre-registration: `research/derivatives/DERIVATIVES_PREREG_2026-11-04.md` (pushed before any results, commit before this one).
Scripts: `analysis/derivatives_preds.py` (out-of-sample totals v4, reproduces the documented 1,446 bets / +119.4u exactly),
`analysis/derivatives_backtest.py`; output `analysis/derivatives_backtest_output.txt`; per-game rows `analysis/derivatives_bets.csv.gz`.

## Data
- Backfill finished: all 813 NBA dates 2021-22..2025-26 (Action Network). DraftKings and FanDuel period lines exist from **2023-24 on**;
  2021-23 is consensus only. So, per the pre-registered fallback, **fit = 2023-24 only, test = 2024-25 + 2025-26**.
- Bet line = Action Network "Open" (the opener); close = DraftKings' last line. Full-game model numbers: honest spread v2 margin
  (step 1 variant B) and live totals v4.

## Main table (test seasons, pre-registered thresholds)
| Market | Bets | CLV (pts) [90%] | Break-even CLV | DK close | At Open | Written rule | 
|---|---|---|---|---|---|---|
| 1H spread (1.5+) | 1,001 | +0.07 [+0.02, +0.12] | +0.66 | 52.1%, −5.9u | −5.4u | fail (units) |
| 1H total (2+) | 1,235 | +0.20 [+0.10, +0.29] | +0.70 | 52.9%, +10.4u | +34.2u | pass |
| 1Q spread (1+) | 1,002 | +0.04 [+0.01, +0.08] | +0.50 | 52.8%, +7.2u | +2.5u | pass |
| 1Q total (1+) | 1,305 | +0.14 [+0.10, +0.19] | +0.48 | 52.6%, +7.7u | −13.2u | pass |
| Team total (2+) | 1,628 | **+0.64** [+0.52, +0.78] | +0.67 | 51.2%, −36.7u | **+51.2u** | fail (units at close) |

Break-even CLV = the CLV needed to pay -110 vig, from how much one point is worth in each market (result sd 8–12 pts).
By season, all three "passes" lost in 2024-25 and won in 2025-26; every units CI at the DK close spans zero (about ±5%).

## Verdict
- **By the letter of the pre-registered rule, 1H total, 1Q spread and 1Q total pass.** But the rule only asked for CLV above 0, and it
  should have asked for CLV above break-even, as every other test in this project does (full-game spreads used +0.77). On that bar
  **none of the five markets pass**: the CLV is real but 3–10x too small to pay the vig.
- **Decision (Claude, per the standing permission to change betting rules; flagged here):** nothing goes live as a bet. The three
  letter-passes are recorded as *shadow* (paper) records once the live period lines are wired in, so the 2026-27 season can check them
  for free. No Fable check needed because nothing goes live; one will run before anything does.
- The pre-registration template now gets a break-even-CLV line for every future market (lesson, not a re-grade).

## Side findings
- **DraftKings' quarter/half spreads are almost purely mechanical:** 1H spread = 0.576 × full spread (R² 0.990, leftover sd 0.46 pts),
  1Q = 0.316 × full (R² 0.978). Totals much less so (R² ≈ 0.69; 1H total = 0.492 × full + 2.2).
  The leftover (how far the period line strays from its usual fraction) does **not** predict the result (|corr| ≤ 0.03).
  So "books derive these mechanically" is true for spreads, but the derivation is *accurate*, not exploitable on its own.
- League shares (2023-24 results): 1H margin 0.534 of the full margin, 1Q 0.273; 1H total 0.500, 1Q 0.250. DK sets its 1H spread at
  0.576 of the full spread, a larger fraction than the realized 0.534, but the leftover test above shows this does not leave an edge. Checked directly: 1H/1Q underdogs at the DK close cover
  48.8–52.8% by size of line (big favorites cover slightly *more*), so there's no 'fade the overstretched favorite' bet either.
- **Team totals:** our model beats the team-total opener by +0.64 pts, steadily (+0.67 / +0.61 by test season, +0.73 in the fit
  season), and +51u if bet at the opener. But that is the full-game totals v4 edge (CLV +1.82) split in two, at higher hold and lower
  limits. Bet the full-game total instead; team totals add nothing new. If DK's team-total *opener* turns out to be as soft as the
  Action Network opener, revisit with live data.
- Direction: 1Q overs beat 1Q unders (CLV +0.44 vs −0.04); the 1Q/1H spread profit came from away sides. Noticed, not tested.

## Takeaways
1. **Quarter and half lines are not the free lunch the playbook expected, at least for model-from-full-game.** DK prices them as a
   near-exact fraction of the full line, and that fraction is right. Edge here would have to come from period-specific information
   (who starts, rotation patterns, first-quarter pace) — not from re-scaling our full-game number.
2. **The pre-registration rule had a hole** (CLV > 0 instead of CLV > break-even). Caught before money went on it; fixed going forward.
3. **The real lesson for Phase 2 (props):** derived markets only beat the book if the model knows something the derivation doesn't.
   Props are priced per player from minutes and usage, which is exactly where our player-level data (minutes, injuries, rotations)
   carries information the book's template doesn't. That stays the next priority.
4. Next derivative idea worth a pre-registration: a **1Q model from starters only** (starting lineups, 1Q minutes from rotations.py),
   since the first ~9 minutes are mostly starters and the book's fraction ignores who actually starts.
