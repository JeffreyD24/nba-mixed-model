# Spreads step 1 (NBA): v2 re-graded with opener-time information — results (Nov 4, 2026)

Pre-registration: `research/spreads/STEP1_NBA_PREREG.md` (pushed first, commit 022af82). Script `analysis/spreads_step1_nba.py`,
output `analysis/spreads_step1_nba_output.txt`, per-game rows `analysis/spreads_step1_nba_bets.csv`.
DraftKings openers 2023-24..2025-26, edge 3+, both teams 10+ games, units at -110. 74% of openers posted before 8 PM the night before.
Break-even CLV (measured): the cover rate rises 3.12 win-% points per point the close moves toward a bet, so a bet needs about
**+0.77 pts** of CLV to pay the -110 vig.

## Main table (v2 full rule unless noted)
| Row | Bets | Win % | Units | Per 100 [90%] | CLV (pts) | By season (24 / 25 / 26) |
|---|---|---|---|---|---|---|
| A: original (lag 0, 8 PM report) | 443 | 58.9% | +55.3 | +12.5 [+5.1, +19.6] | +1.16 | +18.5 / +21.6 / +15.1 |
| **B: honest (lag 1, previous report) — PRIMARY** | **466** | **54.1%** | **+15.1** | **+3.2 [-4.3, +10.3]** | **+0.85** [+0.69, +1.01] | +8.2 / +6.6 / +0.3 |
| B, Oct-Jan part | 373 | 53.4% | +6.9 | +1.9 [-6.0, +9.6] | +0.82 [+0.65, +0.99] | +5.9 / +3.4 / -2.4 |
| B, Feb-Apr part (outside traps) | 93 | 57.0% | +8.2 | +8.8 [-7.6, +25.2] | +0.95 | +2.3 / +3.3 / +2.6 |
| B, home underdogs (excluded) | 369 | 47.2% | -36.8 | -10.0 [-17.6, -2.2] | +0.06 | -17.6 / -6.2 / -13.0 |
| B, all 3+ edges, no filters | 1,098 | 49.5% | -59.5 | -5.4 [-10.1, -0.7] | +0.47 | -34.3 / -9.2 / -16.0 |
| B + Pinnacle cancel (secondary) | 366 | 57.4% | +34.9 | +9.5 [+1.7, +17.3] | +1.22 | +15.6 / +15.1 / +4.2 |
| C: lag 1, 8 PM report | 438 | 59.1% | +56.5 | +12.9 | +1.08 | |
| D: lag 0, previous report | 474 | 54.2% | +16.6 | +3.5 | +0.85 | |

Accuracy: model margin MAE 11.20 vs DraftKings opener 10.93 and close 10.77 (the opener is more accurate than the model).
Reproduction check: row A gives Oct-Jan 357 bets +38.2u and Feb-Apr 86 bets +17.1u vs the documented 355 / +42.1u and 87 / +18.0u.

## Where the original record came from
- **The leak is the 8 PM injury report, not the results lag.** C (lag 1 + 8 PM report) matches A; D (lag 0 + previous report)
  matches B. Model 1's results lag is worth about nothing.
- The 88 bets that only the 8 PM report creates won **69.3%, +28.5u, CLV +1.72**. Bets only the stale report creates: 46.8%, -11.7u.
  On the 355 bets both versions make: 56.3%, +26.8u. The report changes the model by 0.8 pts on average.
- So about half of the original record was injury news that arrived after the opener and moved the line toward the bet.

## Verdict (pre-registered rule, primary row)
CLV +0.85 is at/above break-even (+0.77) and units are positive (+15.1u), so by the rule written in advance **v2 survives honest
timing: keep it.** But read it with the caveats:
- The margin is thin: CLV's 90% interval (+0.69, +1.01) puts a 22% chance on falling below break-even (Oct-Jan alone: 32%), and the
  units interval includes 0. Honest expectation is about **+2 to +3 units per 100 bets**, not +12.
- These are the seasons the rule was chosen on; this can only fail to disprove it, never confirm it.
- The unfiltered model loses (-59.5u). Nearly all of v2's value comes from the filters. The home-underdog filter is backed by 12
  older seasons; the Feb-Apr traps are not (chosen here).

## Takeaways
1. **The honest NBA spread record is about +15u over three seasons, not +55u.** Keep v2 live, but don't size up on spreads; treat it
   as near break-even until the 2026-27 record says otherwise. (This season: watch CLV first; +0.8 pts is the bar.)
2. **Injury news after the opener is the real edge source, and it's large**: bets the 8 PM report created won 69% with +1.7 pts of
   CLV. That is step 3 of the plan. The question to test next is whether those bets are still good at the line available
   **when the report comes out** (9 PM snapshot, and the minute-level lines since Nov 3), not at the stale opener.
3. **Pinnacle disagreeing is a strong cancel signal even with honest inputs** (cancelled bets 42%, -19.8u, CLV -0.50). Since Pinnacle
   posts 5-12 h after DraftKings, it only helps bets not yet placed; the live DON'T BET follow-up is the right form.
4. **Home underdogs stay out** (-36.8u honest, CLV ~0: the model's home-dog edges are noise).
5. Proposed (not applied; needs your approval): update the record quoted in `alert.py` comments and alert text from +42u to the
   honest +6.9u Oct-Jan / +8.2u Feb-Apr, so alerts stop overstating the spread record.
