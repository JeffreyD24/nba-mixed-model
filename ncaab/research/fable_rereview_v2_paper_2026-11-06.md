# Fable re-review: stale-line v1 live + v2 PAPER shadow (Nov 6, 2026)

Independent Fable agent, read-only, on branch `ncaam-stale-line-v2-paper` (commit 912d5313 vs origin/main). First review: NCAAM
`ncaab/research/fable_review_stale_line_v2_2026-11-05/REVIEW.md` (BLOCK v2 as live decider; APPROVE with roles swapped + fixes).

## Verdict: APPROVE WITH FIXES (merge as v1-live + v2-paper; fixes are hardening, none blocks). Must-fix: none.

Verified: v1 decisions, live_bets.csv columns, alert title/body, stop file and notify() byte-identical to main; v2 writes only live_paper_v2.csv
(sent="paper") and never notifies; every v2 load/compute path wrapped so dk_lines.csv, live_poll.json and v1 alerts cannot be stopped by it; stop file
gates v1 only; live_features.py stale-data guard; layer_features.py empty passes -> NaN (research reproduction identical); live_grade v1 / v2paper
(LIVE=False never writes the stop file); ncaab.yml and alert_loop.sh; quoted numbers are the 0.62 ones (625 bets, 57.4%, +58.8u, CLV +1.42);
no orientation bug (opener = -line, e2 = pc2 - opener, neutral swap negates diffs, NaN diff -> 0 as in the fit).

## Should-fix, and what was done (commit after 019057d1)
1. live_alert.py: paper-pick append sat before v1's alert block in the same per-game try -> moved after it, in its own try. DONE.
2. live_alert.py: guard the coefficient file's feature order and length at load -> v2 off with a reason if it differs. DONE.
3. live_features.py: a legitimate no-game day would turn v2 off for a day -> now checks ESPN for each missing day and only skips if games were played
   (or could not be checked) or the gap is over 5 days. DONE (tested: all_games ending Nov 3 -> skip, Nov 4-5 had games).
4. live_grade.py: v2paper "Decision" line labeled "(paper: informational only ...)". DONE.
5. v1_unchanged_check.py gaps (pre-existing state files / append path, missing coefficients file, per-game feature error, neutral-swap sign assertion):
   NOT added. Partly covered by the real-data replay (`v1_unchanged_real_check_output.txt`, today's real Action Network/ESPN responses, identical);
   the git diff shows no v1 line changed. Left as a note.
Checks after the fixes: `v1_unchanged_check_output.txt` (5 scenarios identical), `v1_unchanged_real_check_output.txt` (identical).
