# Pre-registration: leakage audit of the step 3a news bets (NBA spreads)

Written and pushed Nov 4, 2026, before any audit result. Script `analysis/spreads_step3a_leak_audit.py`, output
`analysis/spreads_step3a_leak_audit_output.txt`, results `research/spreads/STEP3A_LEAK_AUDIT_RESULTS.md`.

## Why
Step 3a's news bets (N, T1 10 PM line) went 43-18 (70.5%) with CLV +0.52. CLV that size implies ~52%; 43 wins is ~2.9 SD above
that (one-sided p ~0.002) on the pre-registered primary bucket. The same bets also appear at T0 (before the report) and the line had
moved ~1 pt against them. That pattern is what lookahead looks like, so check for it before any live test.

## Code review (done before the tests, no numbers looked at)
- Report features (`build_report_features.py`): official NBA injury-report PDFs at fixed URLs, 8 PM / 9 PM snapshot of the day before;
  `as_of` read from the PDF header. Player weight = p_miss(status) x minutes before the game / 48 x prior-season EPM. No outcome of game d.
- Model 1 lag 1 (`past = date < d - 1 day`), form, roster strength (`date < d`), EPM (prior season): no game-d information.
- Known small leaks already listed in LEAKAGE_AUDIT_2026-11-03: `p_miss` fit on 2022-25 (includes test seasons). Shared by B and C.
- Cannot re-check the PDF header times here: the official report site is not reachable from this workspace and the parsed
  historical report file is not in the repo. Listed as an open item.

## Tests (C - B differ ONLY in today's injury inputs, so sp_model_C - sp_model_B = the report's adjustment d)
1. **No-report twin (N_B).** Same N definition with model B at the T1 line: B has 3+ edge at T1, B made no v2 bet on that side at the
   opener. If N_B also wins ~70%, the record is not about the report at all (selection / line drift), and the report is not the source.
2. **Placebo.** Shuffle d across games within each season (1,000 shuffles), rebuild N at T1. Share of shuffles with N wins >= observed
   = placebo p. If the real report content drives the record, the placebo collapses toward ~52%.
3. **Where the wins come from.** Split N bets by (a) whether the game-day pre-tip report agreed with the 8 PM report (|d_pretip - d| < 0.5
   pts vs not); (b) whether the bet is ON the team the news helps (d points to our side) vs a bet where d is small and the line moved.
   Leakage signature: wins concentrated where the night-before report "knew" the game-day outcome AND the close did not move toward us.
4. **Oracle check.** C with the game-day pre-tip report (later, more information) at the T2 line. Honest data: the oracle should show at
   least as much CLV as C. If the 8 PM version beats the oracle on wins while CLV stays small, flag.

## Decision rule (fixed now)
- **Leak suspected** if: placebo p >= 0.20 AND N_B wins >= 60% (record not tied to the report; something in the shared pipeline or the
  bet selection carries the result), OR test 3 shows >75% of N wins in the "report agreed with game day, close moved away" cell.
- **Report-driven, no leak found** if: placebo p < 0.05 and N_B < 58%. Then start the live TEST bucket as planned.
- Anything else: **inconclusive**; still start the live TEST bucket (live bets cannot leak) and note the open item.
Nothing live changes from this audit except the TEST bucket, which records only (no push).
