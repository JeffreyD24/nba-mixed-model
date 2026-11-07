# NBA injury Tier A tournament: re-run on the rebuilt missed_value (plan, written Nov 7, 2026 before the re-run)

Why: the pre-registered run (`NBA_INJ_PREREG.md`, 3241f3a; output `nba_inj_choose_output.txt`, Nov 3) used
`data/external/nba_box/missed_value.csv` without Chicago and New Orleans 2013-18 (ESPN's box scores were blank). The file was rebuilt
Nov 7 with those games filled from Kaggle (commit d113d47): BUILD 2014-18 gains the CHI/NO games, and 2013-2019 values change because
ratings use last season's plus-minus and minutes. Requested by Jeffrey.

Steps (fixed before any re-run number is seen):
1. Rebuild the Model 1 predictions the script needs (`analysis/old_seasons_sbr.py . predict`, `nba_tournament.py . predict`) and save
   them under `derived/` (RULE 4).
2. Reproduction check: run `choose` with the OLD missed_value (git d113d47^). It must match the committed Nov 3 output exactly; if not,
   stop and find out why before step 3.
3. Run `choose` with the rebuilt file. Same feature, seasons, filters and decision rules as `NBA_INJ_PREREG.md`; nothing else changes.
   The Nov 3 output is kept as `nba_inj_choose_output_2026-11-03.txt`.
4. The Nov 3 pre-registered verdict (not shown for either market) stays on record. If a market now passes rule 1, the LOCKBOX is run
   once for it under rule 3 (a second look, decides nothing by itself) and reported; nothing live changes without Jeffrey.
