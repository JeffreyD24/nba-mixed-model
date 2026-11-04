# Handoff: NBA injury-news spreads model — reaction-speed study + test plan (Nov 4, 2026)

For a new session. Approved by Jeffrey Nov 4, 3:22 PM: do both parts below, reaction speed first.
Read first: `claude/goals.md`, `claude/findings_log.md`, `claude/spreads_handoff_2026-11-04.md` (rules for spread work),
`research/spreads/STEP1_NBA_RESULTS.md`, `research/spreads/STEP3A_NBA_RESULTS.md`, `research/spreads/SPREAD_OPENER_TIMING_2026-11-04.md`.
Same file in the Project: `claude/news_model_handoff_2026-11-04.md`.

## Why this, and not another spreads model
- Team ratings alone don't beat the NBA opening spread: Model 1 at DK openers 2023-26 (opener-time info) 50.8%, -36.6u; tournament
  2018-22: no candidate beat the opener; DK opener MAE 10.93 vs model 11.20; shrink weight vs the line 0.15.
- The edge is injury news after the opener: the 88 bets only the 8 PM report created won 69.3%, CLV +1.72 (at the opener, not
  bettable). At the 10 PM line after the report (step 3a): 70.5%, +21.1u, but CLV only +0.52 (break-even +0.77). So the market
  absorbs most of the news within ~1-2 h. The open question is how fast, and whether we can get in first.
- Live now: NBA spreads v3.2 (Oct-Jan, both teams 10+ games, no home dogs, Feb-Apr traps, Pinnacle rule, 5+ edges at the opener, the rest
  after the 8 PM report). Honest record ~+2 to +3u per 100. Keep it running; nothing here changes it without approval.

## Part A: how fast does DraftKings price injury news? (do first; it decides whether Part B is worth building)
Question: after a status change or reporter post, how much of the model's swing is in DraftKings' spread after 5, 15, 30, 60, 120 min
and at the close?

Data (all in this repo, live this season):
| What | Where | Notes |
|---|---|---|
| Every official report snapshot | `state/injury_reports_2026_27.csv` | hourly-ish 11:30 AM-9:30 PM; `as_of` = file time |
| Status changes the model rates | `research/injury_decisions.csv` | detected time, report, player, from/to, model swing if he sits (`home_margin_if_sits`, `total_if_sits`), DK line at detection. Only 33 rows so far |
| Reporter posts | `research/bluesky/YYYY-MM-DD.csv` | `posted_at_et`, `lag_min` (our detection lag), players, url |
| Injury notes | `research/news.csv` | `posted_et`, `first_seen_et` |
| Multi-book lines, 5-min | `research/live_odds/nba/*.csv.gz` | Odds API, since Nov 2; DK + FanDuel etc. (`book_last_update`) |
| Action Network per-minute pregame | `research/pregame/*.csv` | since Nov 3; consensus and books |
| DK line history | `state/line_history.csv`, `research/odds/*.csv` | per 5-min check |
| History | `data/odds_history/nba/*.csv.gz` | Odds API 2021-26, hourly by day (denser near tip) |

Method (pre-register before looking at any curve; push `research/spreads/NEWS_SPEED_PREREG.md` first):
1. Events: every status change with |model margin swing| >= 0.5 pts (official report) and every reporter post naming a player whose
   swing is >= 0.5. Event time t0 = the earliest of the report file time and the post's `posted_at_et` (not our detection time).
2. For each event: DK spread at t0 (last value at or before), t0+5/15/30/60/120 min and the close. Absorbed share =
   (line move toward the news) / (model swing). Also the same for FanDuel and other books, to see whether DK lags any book.
3. Report the median and IQR of absorbed share by time, split by source (reporter first vs official report first), status (Out,
   Doubtful, Questionable, return), swing size (0.5-1.5, 1.5-3, 3+), and time of day. Also our own detection lag (t0 to first seen).
4. History (coarse): 2021-26 hourly Odds API lines around the 8 PM / 9 PM / game-day report slots the backtests already use. Raw
   NBA report PDFs can't be fetched from this workspace (nba.com is not on the allowlist); a GitHub Actions workflow can
   (`backtest_v2/download_injury_reports.py` has the URL pattern).
5. Sample: interim read at 100 events, verdict at 200 or Dec 15, 2026, whichever comes first. Say plainly if it's too few.

Decision rule (write it into the prereg unchanged):
- Catchable: for swings of 1.5+ pts, median absorbed share at t0+15 min <= 50% -> Part B worth building with the current 5-min checks.
- Needs speed: mostly absorbed by 15 min but <= 50% at t0+5 -> Part B only with a faster path (1-minute watcher like `opener_watch.py`,
  reporter feed straight to the alert) and our detection lag fixed first.
- Not catchable: >50% absorbed within 5 min -> stop; record "the market prices NBA injury news faster than we can act".

## Part B: the news model (draft the prereg in parallel; run only after Part A says catchable / needs speed)
Model: for a status change, the change in home margin (and total) =
Model 2 (`models_v2.py`: projected lineups x player ratings) re-run with that player's expected minutes redistributed to the rotation
(`rotations.py`, `lineups.py`, `research/minutes/`, `backfill_minutes.py`), instead of today's `p_miss x player value` in `alert.py`
(`player_swings`). Inputs that exist: `data/external/nba_box/player_games_2012_2026.csv.gz` and `missed_value.csv` (CHI/NO 2013-18 empty),
`data/player_epm_2025_26.csv`, `data/p_miss.csv`, `data/last_season_minutes_2025_26.csv`.

Tests (pre-registered, rules in `claude/spreads_handoff_2026-11-04.md`):
1. Accuracy of the swing, 2014-22 (SBR openers/closers, `data/external/sbr/sbr_nba_2011_2021_clean.csv.gz`, never used to choose live
   rules): does the model's swing for players who missed the game (box score) predict the close-minus-open move and the result
   better than the current p_miss approach? Shrink weight on unseen seasons is the test; if it doesn't beat 0.15, stop.
   Seasons: build 2014-18, choose 2018-21, lockbox = 2026-27 forward. Don't use 2023-26 to choose anything (the live rules came from them).
2. Bettability, 2021-26 + live: grade at the DK line at t0 (Part A's event time) with only what was known then. Primary: CLV >= +0.77
   pts; second: units at -110 > 0; report accuracy alongside. Per season and per source.
3. Only then: an alert tier (start as TEST, then PROVISIONAL under `research/PROVISIONAL_BETS.md`), with the threshold set on build
   seasons. Nothing live without Jeffrey's approval; new row in `state/bet_versions.csv` and `config/thresholds.csv`.

## Known limits
- Only 33 rated status changes logged so far; the season gives a few hundred by mid-December. Bluesky coverage is a handful of reporters.
- Our checks run every 5 min inside a ~50-min loop that restarts every 10 min; measure our detection lag before blaming the market.
- History has no intraday reporter timing, so the historical part can test the size of the swing, not who was first.

## Process
- Pull --rebase before every push (bots commit every 5 min). Findings-log entry + repo note with a takeaways section for every result.
- Phone pushes only for bets. Any new data feed goes into the daily health check (`health_check.py`).
- Jeffrey's preferences: plain language, numbers with context, findings on GitHub and in Project docs.
