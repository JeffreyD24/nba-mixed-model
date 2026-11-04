# Step 3a leakage audit (NBA spreads news bets) — results (Nov 4, 2026)

Pre-registration `research/spreads/STEP3A_LEAK_AUDIT_PREREG.md` (commit e300ce6, pushed first). Script
`analysis/spreads_step3a_leak_audit.py`, output `analysis/spreads_step3a_leak_audit_output.txt`, the 63 news-bet rows (incl. pushes) in
`analysis/spreads_step3a_leak_audit_bets.csv`. Same 2,634 games as step 3a.

## Verdict (pre-registered rule): **inconclusive — no leak found, but the report is not the whole story**
- Leak conditions **not met**: placebo p = 0.000 (needed >= 0.20), and only 47% of N wins sit in the "report agreed with game day,
  close did not move toward us" cell (needed > 75%).
- "Report-driven, no leak" **not met** either: the no-report twin N_B won 65.5% (needed < 58%).
- Rule says: start the live TEST bucket anyway (live bets cannot leak) and keep the open item below.

| Test | Bets | Record | Units | CLV |
|---|---|---|---|---|
| N, C model (8 PM report), T1 | 61 | 43-18, 70.5% | +21.1 | +0.52 |
| **N_B, B model (no report), T1** | 55 | 36-19, 65.5% | +13.7 | **−0.18** |
| N bets that are also N_B bets | 26 | 19-7, 73.1% | +10.3 | +0.31 |
| N bets that exist only because of the report | 35 | 24-11, 68.6% | +10.8 | +0.68 |
| Placebo (report adjustment shuffled, 1,000x) | ~109 | median 57.0% [51.0, 62.6] | | |
| Oracle (game-day report), T2 | 91 | 54-37, 59.3% | +12.1 | +0.83 |
| C (8 PM report), T2 | 75 | 49-26, 65.3% | +18.5 | +0.42 |

## What it says
1. **Code review found no game-day information in the inputs.** Report features come from official NBA PDFs by fixed time slot; minutes,
   roster strength, form and team ratings all stop before the game (lag 1). Only known small leak: `p_miss` fit on 2022-25 (shared by
   every model, already listed Nov 3).
2. **The report's content matters.** Shuffling the report adjustment across games drops the record to ~57%; the real one is above every
   shuffle. So the result is tied to which games got which injury news, not to the pipeline in general.
3. **But ~half the record is not the report at all.** 26 of the 61 news bets are also bets the no-report model makes at 10 PM, and that
   no-report bucket wins 65.5% with *negative* CLV. These are games where the line moved ~2.3 pts away from the model overnight
   (mostly injury/rest news the stale model does not know) and fading the move still won. Even the placebo's 57% sits above 52.4%.
   This is a separate, unexplained pattern: **"the stale model fading an overnight line move"**. With CLV below zero it fails the
   goals.md test and is most likely noise, but it is logged in TRENDS as a pattern to watch.
4. **More information gave better CLV but fewer wins.** The game-day oracle beats the 8 PM version on CLV (+0.83 vs +0.42) and loses on
   wins (59% vs 65%). Honest data should not reward *less* information with more wins; this supports "the 8 PM wins are partly luck".
5. **By season:** 54.5% / 77.3% / 82.4% (2024 / 2025 / 2026), so the record is carried by the last two seasons.

## Open item
The PDF header times (`as_of`) could not be re-checked: the NBA report site is blocked from this workspace and the parsed 2023-26 report
file is not in the repo. A one-off GitHub Actions job (the live tracker already downloads these PDFs) can re-download a sample of
night-before 8 PM files and confirm the header time and that they list the next day's games. Low priority: the placebo result does not
point to a leak.

## Takeaways
- Nothing found that invalidates step 3a; the "likely luck" reading stands, slightly strengthened (findings 3-4).
- Go ahead with the live TEST bucket (records only, no push). It will also record the no-report "fade the move" bets so both patterns
  get honest live data.
- Realistic pace: ~20-25 news bets a season, so judge at season's end on CLV with a wide interval, not at 100 bets.
