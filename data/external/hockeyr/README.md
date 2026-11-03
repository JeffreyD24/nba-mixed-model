# hockeyR (NHL expected goals and play-by-play)

Source: github.com/danmorse314/hockeyR (R package, **MIT**) and github.com/danmorse314/hockeyR-data (nightly play-by-play scrape, **no license stated**).
Retrieved Nov 3, 2026.

| Item | What it is | License / handling |
|---|---|---|
| `code/*.R`, `LICENSE_MIT.md` | the package's scraping and xG code (calculate_xg.R, prepare_xg_data.R, scrape_game.R, ...) | MIT: kept, keep the license file with it |
| `xg_model_sysdata.rda` | the package's fitted internal objects (R `sysdata.rda`, includes the xG model) | MIT: kept |
| `team_game_xg_2010_2023.csv.gz` | **derived**: one row per team per game, 2010-11 to 2022-23, 16,353 games: goals, xG for/against (all, 5v5, power play), shot attempts, shots on goal | our own aggregation of public NHL facts; the raw files are not redistributed |
| `build_hockeyr_team_game.py` | how that table was built (re-runnable) | ours |
| `fetch_raw_pbp.sh` | re-downloads the 2 GB raw play-by-play into a git-ignored folder | raw data has no license, so we do not commit it |

## Quality notes
- 13 seasons; regular-season games per year match the real schedule (1,230-1,312; 2012-13 lockout 720; 2020-21 shortened 868). Playoff games are included and labelled (`season_type` P / R).
- Counted goals equal the official final score in 93.1% of team rows. The rest are almost all shootout games (the shootout goal is in the final score, not the goal events).
- hockeyR's xG runs about 4% below actual goals every season (2.82 vs 2.94 per team per game): use it as a relative measure, not as a calibrated goal total.
- The 2023-24 file in hockeyR-data has no xG column (new data format), so it is not in the table. Our own NHL repo covers 2021-22 onward from ESPN with its own xG model.
- Raw files must be read with `encoding="latin-1"` (accented names).

## Personal note and takeaways
- **Why it matters:** the NHL repo's play-by-play starts in 2021. This gives 11 more seasons of shot quality, and the free SBR archive (`../sbr`) has NHL opening and closing moneylines and totals for 2011-2021. Together they allow the first out-of-sample test of the xG model and the "bet at the opener" rule on ten untouched seasons.
- **Caution:** hockeyR's xG is a different model from ours (`nhl_xg_model.py`). Do not mix the two columns in one regression without checking they agree in 2021-23, where both exist.
