# Saved build products (check here BEFORE building anything)

Started Nov 5, 2026 (CLAUDE.md RULE 4; same setup as nhl-mixed-model). Anything that takes more than a minute to build is saved here,
gzipped, with a row in this table, in the same session it is built.

Restore everything into `_tmp/`: `python derived.py .`   Save new build products from `_tmp/`: `python derived.py . --save`, then add rows.

| File(s) | What it is | Built by | Inputs | Built (commit) | Used by |
|---|---|---|---|---|---|
| `props_features.csv.gz` | Props v1/v1b player-game features 2022-23..2025-26 (END-year labels 2023-2026), games with minutes > 0: projected minutes, shrunk per-minute rates, opponent factors, pace, means μ for pts/reb/ast/3PM, plus actuals. Pre-game only (each row uses games before its date). | `analysis/props_v1.py WORKDIR features` | `data/player_stats/season_2023..2026.csv.gz`, `data/odds_history/nba_open_close.csv` | Nov 5, 2026 (this commit) | props_v1.py backtest, props_v2.py, props_v1b_opener.py |
| `../research/market_models/opener_data.csv.gz` (kept with its research, not under derived/) | Market models: one row per NBA game 2021-26 with DK/Pinnacle/FanDuel first-seen and closing totals and pre-opener features (pace/efficiency, recent DK closes, league level, rest, injuries at open). | `research/market_models/build_opener_data.py` | `data/odds_history/nba/`, `data/player_stats/`, `data/training_games.csv` | Nov 5, 2026 (d08f49b era) | opener_models.py, movement_model.py |
| `../research/market_models/*_bets_2025_26*.csv`, `blend_results_reach.json`, `data/movement_model_v1an_reach.json`, `data/blend_v1_reach.json` | Market models step 3-4 test bets and live models (each build ~30-50 s; rebuild only if inputs change). | `export_movement_model.py --an --reach`, `blend_model.py` | as above + `analysis/threshold_sweep_2026-11-04/nba_v4_preds.csv` | Nov 5, 2026 | market_models_live.py |
| `../data/movement_model_v1_reach.json` | NBA totals movement model WITH Pinnacle, honest timing (reachable snapshots), for the Pinnacle-value comparison; not live. | `research/market_models/export_movement_model.py --reach` | as v1an_reach | Nov 5, 2026 | pinnacle_value_check_output.txt |
| `lineup_travel_features.csv.gz`, `roster_features.csv.gz` | NCAAM per-game pre-game layer features 2007-08..2026-27 (lineup/inferred injuries/travel/rest; early-season roster R1-R4), copied from the NCAAM repo's derived/ (same files). Reproduced exactly by `ncaab/layer_features.py` (check: `ncaab/research/layer_features_check_output.txt`). | NCAAM `ncaab/lineup_travel_features.py`, `ncaab/roster_features.py` (~70 s each) | `ncaab/data/all_games.csv`, `ncaab/data/box/*` | Nov 5, 2026 | `ncaab/live_blendc_v2_fit.py` (stale-line v2 coefficients) |
