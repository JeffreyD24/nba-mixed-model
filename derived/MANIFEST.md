# Saved build products (check here BEFORE building anything)

Started Nov 5, 2026 (CLAUDE.md RULE 4; same setup as nhl-mixed-model). Anything that takes more than a minute to build is saved here,
gzipped, with a row in this table, in the same session it is built.

Restore everything into `_tmp/`: `python derived.py .`   Save new build products from `_tmp/`: `python derived.py . --save`, then add rows.

| File(s) | What it is | Built by | Inputs | Built (commit) | Used by |
|---|---|---|---|---|---|
| `props_features.csv.gz` | Props v1/v1b player-game features 2022-23..2025-26 (END-year labels 2023-2026), games with minutes > 0: projected minutes, shrunk per-minute rates, opponent factors, pace, means μ for pts/reb/ast/3PM, plus actuals. Pre-game only (each row uses games before its date). | `analysis/props_v1.py WORKDIR features` | `data/player_stats/season_2023..2026.csv.gz`, `data/odds_history/nba_open_close.csv` | Nov 5, 2026 (this commit) | props_v1.py backtest, props_v2.py, props_v1b_opener.py |
