# Timestamped information data (who played, who was hurt, who started, forecast weather)

Added Nov 3, 2026 for the Opus follow-up work. Question every file answers: **what did the bettor know, and when?**
The edge is in information the opener didn't have yet, so every table says what it is stamped with and what that stamp can and cannot support.

## Status
| Source | Sport | Years | Status | Files |
|---|---|---|---|---|
| nflverse injuries + practice | NFL | 2009-2026 | **downloaded, in repo** | `nfl/injuries_2009_2026.csv.gz` |
| nflverse snap counts | NFL | 2013-2026 | downloaded | `nfl/snap_counts_2013_2026.csv.gz` |
| nflverse schedule/roof/actual weather | NFL | 2009-2026 | downloaded | `nfl/games_2009_2026.csv.gz` |
| nflverse rosters, player ids | NFL | 2009-2026 | downloaded | `nfl/rosters_*.csv.gz`, `nfl/players.csv.gz` |
| NHL box scores (who played, goalies, starter) | NHL | 2010-11 on | **script written, NOT yet run** | `fetch_nhl.py` -> `nhl/` |
| NBA player game logs (who played, minutes) | NBA | 2010-11 on | **script written, NOT yet run** | `fetch_nba.py` -> `nba/` |
| Open-Meteo forecast weather at lead 0-7 days | NFL | 2022 on | **script written, NOT yet run** | `fetch_weather.py` -> `weather/` |
| SBR openers/closers | all | 2011-2021 | already in repo | `../sbr/` |
| The Odds API | all | 2020-26 | already in repo | `data/odds_history/` |

The workspace that wrote this cannot reach api-web.nhle.com, stats.nba.com, ESPN or Open-Meteo (proxy blocks them), so those three scripts were
only tested against mock replies in the documented shape. Run them with the GitHub workflow **Information history download** (Actions -> Run workflow;
`what` = nhl, nba, weather or all). Each saves partial progress and is resumable. After the first run read `nhl/samples/`, `weather/samples/`,
`nba/fetch_log.csv`, `nhl/errors.csv`, `weather/unmatched.csv` before trusting anything (field names are assumed from documentation).

## NFL injuries: what the timestamp really is (read this first)
- **One row per player per week**, the final snapshot, not a Wed/Thu/Fri practice log. Checked on 2024: 6,215 rows, 2 duplicate player-weeks;
  `date_modified` falls on Friday for 77% of rows, Saturday 8%, Wednesday 7%, Thursday 6% (Wed/Thu are Thursday-night weeks).
- `practice_status` = the **last** practice report (Full / Limited / Did Not Participate), `report_status` = the game designation
  (Out / Doubtful / Questionable). Both are Friday-afternoon information. Against a week-early opener that is **the same trap as the fake 54.4%
  of Oct 30**: for opener backtests use the PRIOR week's rows (the live early-number method), never the same week's.
- `date_modified` exists 2010-2024 (2009 almost none). **2025 and 2026 have no timestamp** in nflverse. `snapshot_et` / `snapshot_weekday` are our conversions.
- `report_status` is blank for 55% of rows from 2016 on (about 95% filled before). Likely because "Probable" was dropped after 2015, leaving blank = no designation; not verified.
- A full Wed/Thu practice history for 2011-2019 is NOT here and not available free from nflverse. What this gives: practice-aware sit rates
  (59% / 32% / 21%) tested on 2009-2019, extending the Nov 2 schedule/injury test to the older period, and key-player (QB) status history.
- Snap counts are post-game: only last week's are usable for a prediction.
- `games` contains `temp` and `wind` = ACTUAL game-time weather (the audit's leak) plus `spread_line`/`total_line` (a single line, treat as close-ish, not the opener).

## NHL (`fetch_nhl.py`)
Public NHL API box scores, regular season, 2010-11 to now. Per game: every player who played with toi; goalies with shots against, saves, `goalie_order`
and the API's `starter` flag where present. "Who missed" = on last game's lineup, not this one; includes healthy scratches. Expected starter at the open
is rebuilt from earlier starts (share of last 10, as in the live model), one-day lag. Unknown until run: whether pre-2022 boxscores carry `starter`
(if not, use most-toi goalie; both columns are saved so the choice can be checked).

## NBA (`fetch_nba.py`)
Tries stats.nba.com `leaguegamelog` (one request per season). stats.nba.com often blocks cloud IPs; if so it falls back to ESPN
(~1,300 requests per season, which also gives `started` and DNP reasons). `nba/fetch_log.csv` says which source each season used.
basketball-reference was skipped (rate limits and terms; same information). Existing in repo already: `research/minutes_history` (ESPN, 2022-26).

## Weather (`fetch_weather.py`)
Open-Meteo previous-runs API: forecast issued N days before kickoff (`*_d1..d7`; `_d0` = latest run) for the 4 hours from kickoff, plus a stitched
short-lead forecast (`*_hf`). Columns also carry `actual_temp/actual_wind` for comparison. 2022 on only. Coverage of the lead-N columns by season is unknown
until run (older dates may be empty): check how many `*_d6`/`*_d7` cells are blank before using it for the opener. Dome/closed-roof games skipped;
6 international games with a wrong venue in nflverse go to `weather/unmatched.csv`.

## Takeaways
- The NFL file extends the injury test, it does not rebuild opener-time injury knowledge. The truly opener-time sources remain the live logs
  (`research/injury_decisions.csv`, Bluesky) which only exist from Oct 30, 2026.
- Every new feature from these tables must be shifted to what existed at the opener (prior week, one-day lag for NBA/NHL box scores).
