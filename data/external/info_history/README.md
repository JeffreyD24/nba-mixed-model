# Timestamped information data (who played, who was hurt, who started, forecast weather)

Added Nov 3, 2026 for the Opus follow-up work. Question every file answers: **what did the bettor know, and when?**
The edge is in information the opener didn't have yet, so every table says what it is stamped with and what that stamp can and cannot support.

## Status
Only the NFL part of this folder remains. The NHL, NBA and weather fetchers written here were removed on Nov 3 because another session built
the same jobs from Opus's spec (`research/tournament/DATA_JOBS_FOR_SONNET.md`), with `checks.txt` outputs. Use those instead:
- NBA player-games: `data/external/nba_box/` (workflow `fetch-nba-box.yml`)
- NHL goalies and skaters: nhl-mixed-model `data/external/nhl_box/` (`fetch-nhl-box.yml`)
- NFL forecast weather: nfl-mixed-model `data/external/weather_forecasts/` (`fetch-weather-forecasts.yml`)

| Source | Sport | Years | Files |
|---|---|---|---|
| nflverse injuries + practice | NFL | 2009-2026 | `nfl/injuries_2009_2026.csv.gz` |
| nflverse snap counts | NFL | 2013-2026 | `nfl/snap_counts_2013_2026.csv.gz` |
| nflverse schedule/roof/actual weather | NFL | 2009-2026 | `nfl/games_2009_2026.csv.gz` |
| nflverse rosters, player ids | NFL | 2009-2026 | `nfl/rosters_*.csv.gz`, `nfl/players.csv.gz` |
Rebuild with `python3 -I fetch_nfl.py`. SBR (`../sbr/`) and The Odds API (`data/odds_history/`) were already in the repo.

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

## Takeaways
- The NFL file extends the injury test, it does not rebuild opener-time injury knowledge. The truly opener-time sources remain the live logs
  (`research/injury_decisions.csv`, Bluesky) which only exist from Oct 30, 2026.
- Every new feature from these tables must be shifted to what existed at the opener (prior week, one-day lag for NBA/NHL box scores).
