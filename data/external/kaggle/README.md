# Kaggle tables (archived Nov 5, 2026, data-source audit)

Every Kaggle table the NBA models and backtests read, kept in git so they can be rebuilt even if a dataset changes or
disappears. Built by `tools/archive_kaggle.py`; refreshed by `.github/workflows/archive-kaggle.yml` (box scores daily,
the other two on Mondays). `MANIFEST.csv` lists every file with row count, the Kaggle file date and a content hash.
Files use a fixed gzip timestamp, so a refresh with no new data makes no commit, and git history is a dated record.

| Folder | Kaggle dataset | License | Kept | Used by |
|---|---|---|---|---|
| `eoinamoore/` | eoinamoore/historical-nba-data-and-player-box-scores | CC0 | Games, TeamStatistics, Players, TeamHistories (all history); LeagueSchedule 24-25..26-27; PlayerStatistics 2021-22 on, one file per season | `tracker.py` (downloads it fresh each run), `models_live.py` (referees, possessions, preseason minutes), `backtest_v2/` |
| `nba_betting_2008_2026/` | cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024 | CC0 | all rows | `analysis/old_seasons.py` (2009-10..2020-21 trap tests) |
| `deocheng_epm/` | deocheng/nba-data-1946-2026 | Apache 2.0 | player_epm, player_epm_actual | `analysis/roster_strength.py`, `backtest_v2/build_lineups.py` (only the 2025-26 slice was in git before, as `data/player_epm_2025_26.csv`) |

Not kept: eoinamoore's PlayByPlay.parquet (937 MB) and the *Extended files, which no script reads; PlayerStatistics before
2021-22. Run `python tools/archive_kaggle.py .` to re-save; `--only eoin|betting|epm` for one dataset.

## Personal note and takeaways
- Before this, the live tracker's referee and preseason-minutes inputs (Models 2 and 3) existed only for the minutes a
  morning run was alive. Now each day's version is in git.
- The 2025-26 season's PlayerStatistics here can be compared against `data/box_2025_26.csv` if a box-score question ever
  comes up; they come from the same source.
