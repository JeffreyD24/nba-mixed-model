# NBA model tournament: results (Nov 3, 2026)

Pre-registration: `NBA_PREREG.md` (commit 1fa4f26). Picks committed before the lockbox (commit 9509718). Code: `nba_tournament.py`.
Outputs: `nba_choose_output.txt`, `nba_choose_results.csv`, `nba_picks.json`, `nba_lockbox_output.txt`, `nba_lockbox_diagnostic.txt`.
All candidates use box scores only (no injuries, no shots), the one-day lag, and are anchored to the opener with a weight fit on BUILD.

## Verdict
- **Spreads: nothing beats the opener.** Best was the stack (+0.24 MSE improvement on CHOOSE, 13% chance it was really negative); Model 1
  alone +0.12 (25%). No candidate passed, so per the rules there was no lockbox run. Ten seasons, every approach: NBA spreads at the opener
  are not beatable with team ratings.
- **Totals: the stack beats the opener, out of sample, at DraftKings' real openers.** LOCKBOX 2023-26 (refit on 2014-2022, opened once):
  MSE improvement **+2.03** (90% range +0.73 to +3.36, 1% chance negative); untuned bets **1,647, 53.7%, +42.5u**, closing line moved
  toward the bets by **+1.38 points**; every season positive (+7.2, +3.2, +16.6, +15.5u; CLV +1.10 to +1.58).

## CHOOSE (2018-19 .. 2021-22, SBR openers)
| Totals candidate | Weight | MSE improvement [90% range] | Bets | Win % | Units | CLV (pts) | Pass |
|---|---|---|---|---|---|---|---|
| simple averages | 0.05 | −0.06 [−0.31, +0.17] | 0 | | | | no |
| Model 1 | 0.07 | +0.23 [−0.03, +0.49] | 6 | | | | no |
| Model 1 + last-10 form | 0.09 | +0.59 [+0.25, +0.92] | 20 | 80% | +10.5 | +5.95 | yes |
| **stack** | fit | **+1.40 [+0.74, +2.03]** | 469 | 54.8% | +21.6 | +1.30 | **yes (pick)** |
| Spreads candidate | | | | | | | |
| Elo (538 defaults) | 0.05 | −0.03 [−0.15, +0.10] | | | | | no |
| simple averages | 0.03 | +0.01 [−0.06, +0.08] | | | | | no |
| Model 1 | 0.13 | +0.12 [−0.18, +0.41] | 233 | 54.1% | +7.5 | +0.57 | no |
| Model 1 + form | 0.13 | +0.17 [−0.13, +0.46] | 221 | 52.9% | +2.4 | +0.61 | no |
| stack | fit | +0.24 [−0.11, +0.59] | 408 | 54.4% | +15.8 | +0.54 | no |

The totals stack (refit on 2014-2022): `result - opener = 0.60 + 0.26 x (Model 1 - opener) - 0.02 x (simple - opener) + 0.05 x form
+ 0.43 x altitude + 0.35 x both teams rested`.

## Is it just "lean over"? (diagnostic after the lockbox; does not change the verdict)
- 94% of the stack's lockbox bets were overs: 834-716 (53.8%), +42.2u, CLV +1.27. Unders 51-46.
- Blind "bet every over" at DraftKings' openers 2023-26: 50.1% (a loser at -110). So the stack picks *which* overs well.
- Stack with its constant removed: still +1.95 [+0.96, +2.97], 1,086 bets 53.0%, CLV **+1.94**. The information is real, not the lean.

## What this means
1. **The simple stack beats the opener with box scores alone.** Model 1 (weight 0.26 inside the stack), altitude, rest and a small form term,
   anchored to the line. It's simpler than the live totals model (no shots, no injuries, no luck term) and was chosen without touching 2023-26.
2. **The live totals model (Model 1 + luck + form + altitude, v4) did better on the same seasons** (+129.7u lag-fixed, ~56.7%), but its pieces
   were chosen on those seasons. The honest comparison is the 2026-27 live season: track the stack side by side.
3. **Spreads: stop spending effort on team ratings.** If NBA spreads can be beaten at all, it's with information the opener lacks (injury news,
   rest decisions), not better ratings.

## Next (in order)
1. ~~Track "NBA totals stack" as a side-by-side record~~ **Started Nov 3, 2026 (user approved):** `stack_record.py` (morning run) -> `state/picks_log_stack.csv`, coefficients frozen in `data/stack_totals.json`; reproduces the 2025-26 lockbox exactly. v4 unchanged. Bets start once both teams have 10+ games (mid-November).
2. Tier B on 2022-26: does adding the night-before injury report and the shooting-luck term to the stack help? (already-seen seasons, labeled)
3. Data job (Sonnet + GitHub Actions): box-score "missed the last game" history back to 2012 from the NBA stats API, so injuries can be tested
   on ten seasons the same way.
4. Same tournament for the NHL (SBR + hockeyR are ready) and the NFL (needs nflverse injury/practice history 2011-21).
