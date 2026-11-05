# NBA official injury report history (every game-day report, 2021-22..2025-26)

- **Source:** official NBA injury report PDFs, `https://ak-static.cms.nba.com/referee/injury/Injury-Report_<date>_<time>.pdf`
  (public, no license stated: only parsed rows are committed, never the PDFs).
- **What's fetched:** for every game date, every file from 10 AM to 10 PM ET that day and 5-10 PM the night before, trying
  `HHPM`, `HH_00PM`, `HH_15PM`, `HH_30PM`, `HH_45PM`. `as_of` = the time printed in the report itself.
- **Files:** `reports_SEASON.csv.gz` (one row per report file x listed player: snapshot, as_of, game_date, game_time_et, matchup, team,
  player, status), `download_log_SEASON.csv` (every name tried), `run_log.txt`.
- **How to re-run:** edit `REQUEST.txt` (seasons line) and push, or dispatch `injury-history.yml`.
- **Parser:** `parse_injury_reports.py` (same one the live tracker uses).

## Quality problems
- The NBA CDN throttles fast scrapers with 403s (the first attempt got 26 files for 2021-22). The downloader now uses 3 threads, a short
  pause, and a "canary" file to tell throttling from missing files.
- File names: `HHPM` hourly 2021-25 (report stamped HH:30); 2025-26 also `HH_MMPM` every 15 min. ~2 missing names a season.
- Files per season: 3,133 / 3,114 / 3,027 / 3,095 / 8,917 (2021-22 .. 2025-26); `as_of` parsed for 100%; player-name match to box scores 98.8%.

## Personal note and takeaways
- First use: `research/spreads/REPORT_SLOT_RESULTS.md`. DraftKings prices a daytime report's news mostly within ~26 minutes.
- Every report since 2021-22 now sits in the repo, so injury questions no longer need the live season to fill up first.
