# NBA official injury report history (every game-day report, 2021-22..2025-26)

- **Source:** official NBA injury report PDFs, `https://ak-static.cms.nba.com/referee/injury/Injury-Report_<date>_<time>.pdf`
  (public, no license stated: only parsed rows are committed, never the PDFs).
- **What's fetched:** for every game date, every file from 10 AM to 10 PM ET that day and 5-10 PM the night before, trying
  `HHPM`, `HH_00PM`, `HH_15PM`, `HH_30PM`, `HH_45PM`. `as_of` = the time printed in the report itself.
- **Files:** `reports_SEASON.csv.gz` (one row per report file x listed player: snapshot, as_of, game_date, game_time_et, matchup, team,
  player, status), `download_log_SEASON.csv` (every name tried), `run_log.txt`.
- **How to re-run:** edit `REQUEST.txt` (seasons line) and push, or dispatch `injury-history.yml`.
- **Parser:** `parse_injury_reports.py` (same one the live tracker uses).

## Quality problems (filled in after the run)
_pending_

## Personal note and takeaways
_pending (written once the run is checked)_
