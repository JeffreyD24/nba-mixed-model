# NBA mixed-model tracker

A mixed model (team offense/defense random effects, home court, back-to-backs, and official
pre-game injury reports) that predicts NBA spreads and totals, runs itself on GitHub every
day, and sends phone alerts when it disagrees with the posted line.

## What runs, and when

| Workflow | Schedule | What it does |
|---|---|---|
| **Morning model run** (`morning.yml`) | Daily, 11:41 AM EDT / 10:41 AM EST | Downloads the latest results and box scores, downloads and parses any new official injury reports, refits the model on 2021-22 to 2025-26, walks forward through 2026-27 with no lookahead, **locks** predictions for today's games (timestamped, never changed afterward), grades finished games and alerts, and rebuilds `NBA_Live_Tracker.xlsx`. |
| **Line check and phone alerts** (`alerts.yml`) | Every 5 minutes (GitHub sometimes runs these late or skips some) | Pulls the newest injury report and the current DraftKings lines from ESPN, re-predicts today's games without refitting, and sends one ntfy push per game and market when the model differs from the current line by **3+ points**. |

Both can also be started by hand from the **Actions** tab (**Run workflow**).

## Alerts

- **Rule:** spreads and totals, model vs. the current line, edge of 3 points or more. One alert per game per market.
- **Safeguards.** An alert is held back, and logged with the reason, when:
  - the newest official injury report is more than 3 hours old (overnight and early morning), or
  - the line has moved 3+ points since it opened, which usually means news the model doesn't have yet.
- Every alert, sent or held back, goes into `state/alerts.csv` and the **Alerts** sheet of `NBA_Live_Tracker.xlsx`, and is graded the next morning.
- Phone delivery uses [ntfy](https://ntfy.sh). The topic name is stored as the repository secret `NTFY_TOPIC` and never appears in the code.

Settings live at the top of `alert.py`: `THRESHOLD`, `MAX_LINE_MOVE`, `MAX_REPORT_AGE_H`, and `WINDOW` (set it to `(16, 0, 19, 0)` to alert only 4–7 PM ET).

## Files

- `tracker.py`: the morning run. `alert.py`: the intraday check. `espn.py`: lines.
- `nba_mixed_model.py`: the mixed model (Henderson's equations, REML variance components, walk-forward).
- `build_report_features.py`, `parse_injury_reports.py`: official injury reports to model features.
- `build_tracker_workbook.py`: builds `NBA_Live_Tracker.xlsx`.
- `data/`: training seasons with features and lines, last season's minutes and player ratings, and how often each injury status means a player sits.
- `state/`: everything the runs build up. `picks_log.csv` holds the locked daily picks, `alerts.csv` the phone alerts, `injury_reports_2026_27.csv` every parsed report, and `today_model.json` today's model for the intraday checks.

## How to read the results, and what to expect

- **The honest test** is the pre-chosen rule on the **Summary** sheet: totals against the opening line at edge 4+, using picks locked before tip-off. Judge it only after about 150 bets.
- **Phone alerts fire against later lines,** which are sharper than openers. In every backtest (12 seasons), the model never beat closing lines; its only profit came against opening lines. Expect alerts to land near break-even (52.4% at -110) unless the live data says otherwise.
- **Don't change thresholds mid-season** based on what has been hitting. That turns a fair test into a fitted one.
- **Treat it as a test, not a betting system,** until a full season of live results says otherwise.

## Notes

- Data sources: Kaggle (`eoinamoore/historical-nba-data-and-player-box-scores`) for results and minutes, official NBA injury reports (`ak-static.cms.nba.com`), and ESPN's public odds feed (DraftKings).
- GitHub pauses scheduled workflows in public repos after 60 days without activity. The daily commits from these runs count as activity, so this should not happen during the season.
