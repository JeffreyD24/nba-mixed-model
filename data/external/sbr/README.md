# Free historical odds: SportsbookReview archive, 2011-2021 (cleaned)

Added Nov 3, 2026. Source: the pre-scraped archives in github.com/FinnedAI/sportsbookreview-scraper (MIT licensed scraper;
the odds themselves come from sportsbookreview.com). The untouched original is kept next to the cleaned files so nothing is lost.

## What is here
| File | What it holds |
|---|---|
| `sbr_<sport>_2011_2021_clean.csv.gz` | one row per game: teams, final score, **opening and closing** lines (NBA/NFL: spread, total, closing moneyline; NHL/MLB: opening and closing moneyline, totals, closing run/puck line) plus quality flags |
| `sbr_raw/<sport>_archive_10Y.json.gz` | the archive exactly as downloaded (do not edit) |
| `sbr_cleaning_report.txt` | what the cleaning script found and fixed, with the checks it ran |
| `clean_sbr.py` | the cleaning script (`python3 -I clean_sbr.py SRC_DIR OUT_DIR`), re-runnable |

Coverage: NBA 13,893 games, NFL 2,946, NHL 13,668, MLB 25,586 (seasons 2011-2021). **Season labels are the START year** (NBA/NHL 2011 = 2011-12,
and 2021 runs through June 2022). Our own NBA files label seasons by the END year, so SBR 2021 = our 2022. Team names are nicknames
("Knicks", "NewJersey", "Seventysixers", "Golden State"), not our codes; map them before joining.

## Quality problems found (and what was done)
1. **10 scrambled playoff rows per sport** (a team name stored as the number 0): dropped.
2. **Closing spread and closing total swapped** in 6.7% of NBA rows (933) and 8.8% of NFL rows (259): the "spread" column holds 178.0 and the
   "total" column holds 4.0. Repaired by swapping back; the sign comes from the closing moneyline (else the opening spread).
   Repaired rows are flagged `close_repaired = 1`.
3. **The swapped rows are not random**: they are mostly pick'em / tiny-spread games, and about 18% of them also show an opening spread of
   exactly 0.0, so their openers are unreliable. Our check: repaired rows' closing spread agrees in sign with the opener only 83% of the time
   (normal rows 99%) and moves 1.9 points from open to close versus 1.0 in normal rows.
4. A few openers are plainly broken (NBA open totals of 19.5 and 1,955.5): flagged `open_ok = 0` (13 NBA rows, 4 NFL).
5. NHL and MLB: no swaps found; a handful of totals/moneylines outside a sane range are flagged.

## Which rows to use
- Spread backtests: `spread_trusted = 1` (NBA 12,949 of 13,893; NFL 2,685 of 2,946).
- Total backtests: `total_trusted = 1` (NBA 13,874; NFL 2,941).
- Always run a backtest both ways (all rows vs trusted rows) once. If the answer changes, the data is the reason, not the model.

## Personal note and takeaways
- **Why it matters:** until now our openers only went back to 2021-22 (we noted "no openers before 2021"). This gives ten more seasons of
  opening AND closing lines for all four sports, so the "bet at the opener" rule can finally be tested out of sample on seasons the models never saw.
- **Biggest trap:** the corrupted rows are the close games. A backtest that silently drops them tests a different game mix than the one you will bet.
- **Not a live source.** It ends in 2021 and the opening line here is SBR's consensus-style opener, not necessarily the DraftKings opener
  we bet at. Treat results as direction, not exact ROI.
- **Licensing:** the scraper is MIT; the underlying odds belong to sportsbookreview.com. Fine for private research. This repo is public, so
  think twice before redistributing it beyond that.
- **Not collected on purpose:** the BeatTheBookie closing-odds dataset (soccer only, no use for our sports) and hockey xG sources
  (the NHL repo already has its own xG model).
