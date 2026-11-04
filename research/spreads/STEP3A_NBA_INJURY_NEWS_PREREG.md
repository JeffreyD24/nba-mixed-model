# Pre-registration: NBA spreads, injury news after the opener, graded at the line when it can be acted on

Written and pushed Nov 4, 2026, before any result. Script `analysis/spreads_step3a_nba.py` (output `_output.txt`), results
`research/spreads/STEP3A_NBA_RESULTS.md`. Follows step 1 (`STEP1_NBA_RESULTS.md`): the 88 bets only the 8 PM night-before report
creates won 69% with CLV +1.72 at the opener, which is not bettable (the opener posts before the report). Question: is there still
an edge at the DraftKings line available AFTER the report is out?

## Setup
- DraftKings 2023-24..2025-26; both teams 10+ games; v2 filters (no home underdogs; Feb-Apr outside the traps); MAX_PRICE -120 not
  applied (snapshot prices at these times are mostly -110; noted); units at -110.
- Model "B" = step-1 honest opener model (lag 1, previous game's report). Model "C" = lag 1 + 8 PM night-before report.
- Only games whose home team's opening-side report is the 8 PM or 9 PM night-before snapshot (the others fell back to a game-day
  or previous-game report and are excluded).
- Lines (last DraftKings snapshot at or before): **T1 = 10:00 PM night before** (report out ~1-2 h; what the news is worth);
  **T2 = 7:00 AM game day** (the first time Jeffrey is awake to bet); diagnostic only, not bettable: T0 = 8:00 PM (just before the report).

## Bet sets (edge 3+ vs the line at that time, C model)
1. **N, news bets (PRIMARY):** C has a 3+ edge at the line, and B did not make a v2 bet on that side at the opener.
2. W, wait-and-bet: every v2 bet from C at the line, minus lines that moved 0.5+ against the bet since the open (live PASS rule).
   Compared with step-1 B at the opener on the same games.
3. B + N: opener bets as in step 1, plus news bets at the line (one bet per game; skip N if B already bet that game).

## Measures
CLV vs the DraftKings close (primary; break-even +0.77 pts from step 1, 90% range +0.64 to +0.98), units at -110 with 90%
bootstrap per 100 bets, win %; per season. For N also: how far the line had already moved toward the news by T1/T2.

## Decision rule (N, fixed now)
- T1 CLV >= +0.77 and units > 0: the post-report news is a real edge at a bettable time.
- T2 also passing: actionable for Jeffrey's schedule; propose a "news bet" alert design (morning re-check) for approval.
- T1 passes but T2 fails: the edge exists but needs an overnight bet path (automation or a morning-only alternative); report.
- T1 CLV <= 0 or units <= 0: not shown; the market prices the report before we can act.
Same seasons v2's filters were chosen on; the news-bet rule itself is new. Nothing live changes without approval.
