# NBA tournament, injuries in Tier A: pre-registration (written Nov 3, 2026, ~7:40 PM ET, before any result with the new feature)

Follows `NBA_PREREG.md` / `NBA_RESULTS.md`. Data job A (`data/external/nba_box/missed_value.csv`) now gives a box-score "missed the last game"
value back to 2012, so injuries can be tested on the same BUILD/CHOOSE seasons as everything else instead of only 2022-26.
Code: `research/tournament/nba_injury_tier_a.py` (reuses `nba_tournament.py` unchanged; its CHOOSE output was re-run tonight and reproduced
exactly, no diff).

## Feature (fixed now)
- `missed_value_z_prior` per team and game (standardized with the PRIOR season's mean/sd, so point-in-time; reference game is at least
  2 days before the game, so known at the opener). Positive = good players missed the team's last game.
- Spreads: `inj_sp = z_away - z_home` (positive = home relatively healthier). Totals: `inj_tot = z_home + z_away`.
- Sign is fitted, not assumed.

## Candidates
- **6 stack** (unchanged, the incumbent).
- **7 stack + missed**: the same stack OLS with the one extra column (`inj_sp` for spreads, `inj_tot` for totals), fit on BUILD.
Both are scored on exactly the same games: those where both teams have a missed-value row (this drops Chicago and New Orleans games in
2013-18, where ESPN box scores are empty) plus the usual filters (10+ games each, trusted lines).

## Seasons and scoring (same as NBA_PREREG)
BUILD 2014-2018 (fit), CHOOSE 2019-2022 (verdict), ΔMSE vs the opener with game-day bootstrap, untuned bets at -110, CLV in points.
New: **paired ΔMSE of 7 minus 6** on the same game-days (2,000 draws).

## Decision rules (set now)
1. **Injury info adds to the stack** (per market) if on CHOOSE the paired ΔMSE (7 - 6) has its 90% interval above 0 AND candidate 7
   passes the original rule (ΔMSE interval above 0 and bets' CLV > 0).
2. Spreads: nothing passed before. If 7 passes rule 1 for spreads, it is the first NBA spread candidate to beat the opener on CHOOSE.
3. LOCKBOX (2023-26, DraftKings openers, refit on 2014-2022) is run once for any market where rule 1 passes. It is a **second look**:
   the stack lockbox was already opened for totals, the live injury rules were developed on these seasons, and the RAPM rating scale
   changes in 2023 (z_prior mean +0.41 that season). Its result is reported with that label and decides nothing by itself.
4. No change to the feature, sign convention, seasons or filters after this commit; anything else is exploratory.
5. Nothing live changes without the user's approval; a promotion is a new version with its own record.
