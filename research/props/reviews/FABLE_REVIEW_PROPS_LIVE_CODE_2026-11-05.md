# Fable review of the live prop alert code (Nov 5, 2026)

Before the first real-money alert. All five must-fix items were fixed the same evening (commit after this file). Verbatim:

**Verdict: fix first** (items 1–3 before 6 AM; 4–5 same day). Dry runs in `/tmp/claude-0/fable3/` (scratch copy of the repo + stubbed `actionnet`): `live()` runs end to end on `research/props_fd/2026-11-05.csv` (60 lines at opener, 0 at EV ≥ 5%; forcing the floor off produced well-formed alerts), guards (hours / April / live_from), tz handling (naive ET throughout), dedupe key and name matching (28/28 FD names matched, no duplicate names in `S`) all behave. `tracker.grade_my_bets` passes prop rows through cleanly; alert.py / bailout / market_models / edge_stats readers tolerate `market=prop`.

**Must fix**

1. `log_bet.py:102-105` — `row.update(player=, side=, stat=)` runs **after** `B.to_csv`, so the columns are never saved. `grade_my_props` then crashes (`AttributeError: 'Series' object has no attribute 'player'`, `props_shadow.py:286`); logged props are never graded. Move the update above the `concat`. Verified: with the columns filled, grading is correct (LeBron under 10.5, 13 pts → L, −1.0).
2. `props_shadow.py:250-253` — a missing runner price (suspended market → `None` → NaN) passes both the 5-cent check and `ev < ev_min` (NaN comparisons are False) and **sends a real alert reading "chance nan%, EV +nan%"** (reproduced). Skip non-finite prices and apply the backtest's bad-quote filter (100 ≤ |odds| ≤ 1000, `props_v1b_opener.py:26`).
3. `props_shadow.py:228-233` — "opener = first row in the date file" has no evidence of a preceding run. Tonight's first run with the new code stamps every already-posted Nov 6 prop as an opener seen ~17:xx with a 4h+ lead; any Actions gap does the same. Log each snapshot time (e.g. `state/props_fd_runs.csv`) and require a run within ~45 min before `first_seen`.
4. Rule difference: the backtest bets **at** the opener unconditionally; live alerts only lines still at the opener at the first 6 AM–8 PM run, i.e. for overnight openers it conditions on "unmoved for hours". Backtest profit came with lines moving our way (+0.29); this slice was never tested. Either alert only when `first_seen` is within the last ~40 min, or test the "unchanged at 6 AM" slice on BettingPros snapshots (RULE 2) before relying on it.
5. Missing timing guard: backtest drops rows whose previous game was on/after the opener's ET date (`props_v1b_opener.py:44`); live uses last night's box for a line posted last evening. Add `last_date` to `player_state()` and skip when `last_date >= first_seen` date.

**Should fix / notes**
- 5-cent tolerance computes EV at the opener but Jeffrey gets the current price (−110→−115 cuts EV ~2.4 pts); require EV ≥ 5% at the current price too (`:252-253`).
- Pace denominator is last season's mean (230.4; `nba_open_close.csv` ends 2026-04-12) and numerator the current DK total, vs. opener / running season mean in the backtest — ~1% mu drift, acceptable.
- `actionnet.lines` failure kills the whole run (no alerts for 30 min); wrap it (pace=1, opponent from FD `home/away/team_abbr`).
- Workflow 11 AM step now needs `M < 30`; cron jitter can skip the daily grade/pick.
- `grade_my_props` "void" → `bet_record.py:70` shows pending forever.
- Pick regex rejects "Bane under 21.5 points" (number not allowed).
- Unverified: FanDuel's NBA page listing tomorrow's events (API 403 via proxy here).
- Review item 7 (opener must be market-wide first, not FD-first-while-DK-exists) is not checked live; note it in the registry row.
