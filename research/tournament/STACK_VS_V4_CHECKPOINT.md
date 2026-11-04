# NBA totals: when and how we decide between v4 and the stack (written Nov 3, 2026, before any 2026-27 stack pick exists)

Background: on the same games 2024-26 v4 beat the close by more than the stack (CLV +1.82 vs +1.37 pts), but v4's pieces were chosen on those
seasons (`NBA_V4_VS_STACK_PREREG.md`, `analysis/nba_v4_vs_stack_output.txt`). The 2026-27 side-by-side record is the clean test.
Records: v4 = the live total alerts that were sent (`state/alerts.csv`, first sent alert per game, CLV vs the line alerted);
stack = `state/picks_log_stack.csv` (`stack_record.py`, graded at the DraftKings opener). `stack_record.py` prints the numbers below every morning.

## Games compared
Only games where the stack is eligible (both teams 10+ games, opener present). Split into three groups: **v4 only**, **stack only**, **both**.

## Scoreboard
**CLV in points** (closing total minus the line bet, in the bet's direction). Wins and units are reported but do not decide, because a season
is too few bets to separate skill from luck on results.

## Checkpoint 1: the All-Star break (first morning run after the Feb 21, 2027 game)
- Needs at least **100 bets in each** of the v4-only and stack-only groups; otherwise nothing is decided and it carries to checkpoint 2.
- **Switch to the stack** only if the stack-only bets' mean CLV is higher than the v4-only bets' mean CLV with the 90% interval of the difference
  (resampling game days) above 0, **and** the stack's overall CLV is at least v4's.
- **Keep v4** in every other case (the incumbent stays unless the challenger clearly wins).
- A switch is made only with the user's approval and goes in as a new version (`state/bet_versions.csv`), never as an edit to v4.

## Checkpoint 2: end of the regular season (first morning run after the last regular-season game)
Same test on the full season. Its result decides which totals model starts 2027-28 (again with the user's approval, as a new version).

## What does not change before then
v4's rules, thresholds and weights stay as they are for the season (no mid-season changes), and the stack's coefficients stay frozen
(`data/stack_totals.json`). Anything looked at besides this test is labeled exploratory.
