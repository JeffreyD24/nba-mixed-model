# Pre-registration: NBA spreads v2, re-graded with opener-time information (spreads plan step 1, NBA)

Written and pushed Nov 4, 2026, **before any result was computed**. Script: `analysis/spreads_step1_nba.py`
(output `analysis/spreads_step1_nba_output.txt`, findings `research/spreads/STEP1_NBA_RESULTS.md`).

## Question
The live NBA spread rule (v2) was chosen on a record of +42u (355 bets, Oct-Jan, no home underdogs) and 87 bets +18u (Feb-Apr
outside the traps) at DraftKings openers 2023-24..2025-26. That record used information the bettor did not have when the opener
posted (openers mostly post 2-7 PM the night before):
1. Model 1 fit with results through the night before (lag 0) instead of two nights before (lag 1, the live morning lock).
2. The 8 PM night-before injury report.
3. Last-10 form and roster strength computed through the night before.
4. Feb-Apr standings categories computed through the night before.
What is the record when every input is limited to what was known when the opener posted?

These seasons were used to choose the rule, so this test **cannot confirm** v2. It can only show whether the record survives
honest timing. A pass here means "not disproved", not "proven".

## Variants (all at DraftKings openers 2023-24..2025-26, edge 3+, both teams 10+ games, units at -110, 1 unit per bet)
Model number = Model 1 + 0.11 x last-10 margin form + 0.57 x roster-strength difference (live weights; not re-fit).
| Row | Model lag | Injury report | Form / roster / standings | Role |
|---|---|---|---|---|
| A | 0 | 8 PM night before | through the night before | reproduction of the original record (check only) |
| B | 1 | each team's previous game's report | through two nights before (teams that played the night before use their value from before that game) | **PRIMARY: bettable when the opener posts** |
| C | 1 | 8 PM night before | as B | isolates the injury-report effect |
| D | 0 | previous game's report | as A | isolates the results-lag effect |

Within each row, report: v2 full rule (Oct-Jan no home dogs + Feb-Apr outside traps), Oct-Jan part, Feb-Apr part, home underdogs
(excluded by the rule), and all 3+ edges with no filters.
Secondary (B timing only): B + Pinnacle cancel (drop bets whose Pinnacle first spread is on the other side; only possible for a bet not
yet placed when Pinnacle posts, typically 5-12 h later).

Recent-arrival trap flag is reused from `analysis/late_season_games.csv` (computed through the day of the game; a 1-day lag on a
30-day window is ignored, noted as a limitation).

## Measures (goals.md order)
1. **CLV (primary):** points the DraftKings close moved toward the bet from the opener, averaged over bets; also % of bets that beat
   the close. Break-even reference: from all games, slope of cover rate at the opener on (close - opener) in points;
   break-even CLV = 2.4 win-% points / slope (a 52.4% bet at -110 against a 50% close).
2. **Units (second check):** at -110; per season and total; 90% bootstrap interval for units per 100 bets (2,000 resamples of bets).
3. **Accuracy (alongside):** win %, and model margin MAE vs the opener's MAE on the same games.

## Decision rule for the PRIMARY row, v2 full rule (fixed now)
- CLV at or above break-even and units > 0: the record survives honest timing; keep v2.
- CLV > 0 but below break-even: the model knows something but not enough to pay the vig; recommend moving NBA spreads back to
  test-only.
- CLV <= 0: no information beyond the opener; the original record was leak and luck; recommend test-only.
- Units are the second check: if units and CLV disagree, report it using the goals.md table (positive CLV + negative units =
  likely bad luck; negative CLV + positive units = likely luck or a leak).
Nothing live changes without Jeffrey's approval.
