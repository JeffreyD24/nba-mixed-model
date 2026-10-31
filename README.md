# NBA mixed-model tracker

A mixed model (team offense/defense random effects, home court, back-to-backs, and official
pre-game injury reports) that predicts NBA spreads and totals, runs itself on GitHub every
day, and sends phone alerts when it disagrees with the posted line.

## What runs, and when

| Workflow | Schedule | What it does |
|---|---|---|
| **Evening model run** (`evening.yml`) | Daily, 9:33 PM EST / 10:33 PM EDT | Refits the model on 2021-22 to 2025-26, walks forward through 2026-27 with no lookahead, and **locks** predictions for the **next day's** games using the official 8 PM injury report. That's the same setup the backtests used, and it happens before most opening lines are posted. Locked picks are never changed. |
| **Morning run** (`morning.yml`) | Daily, 11:41 AM EDT / 10:41 AM EST | Adds last night's results, grades finished games and alerts, refreshes today's model with the latest data, and rebuilds `NBA_Live_Tracker.xlsx`. |
| **Line check and phone alerts** (`alerts.yml`) | All day, every 5 minutes | GitHub's scheduler often starts frequent jobs 30–60 minutes apart, so each run checks every 5 minutes for about 50 minutes by itself (`alert_loop.sh`), and the next run queues behind it. It pauses while a morning, evening or bet-logging run is saving. Each check covers today's and tomorrow's games: pulls the newest injury report and the current DraftKings lines (from Action Network, refreshed about every 30 seconds; ESPN's copy is the backup and supplies DraftKings' opening line), re-predicts without refitting, and sends one ntfy push per game and market when the model differs from the current line by **3+ points**. |

All three can also be started by hand from the **Actions** tab (**Run workflow**).

## How picks are tracked

**The scorecard:** every spread and total whose **opening line** differs from the locked model number by **3+ points** counts as a bet at the opening line, even if the line moved before a bet could be placed. That measures the model itself, not your timing. It's the highlighted rule on the **Summary** sheet.

## Alerts

- **What an alert says:** the model's number, the current DraftKings line (marked "opening line" if it hasn't moved; otherwise it shows where it opened), the edge now, and the edge at the opening line.
- **Rule:** spreads and totals, model vs. the current line, edge of 3+ points. One alert per game per market.
- **Caution alerts.** When the edge is there but a safeguard is triggered, the alert is still sent, titled **CAUTION**, at normal priority, with the reason and a reminder to bet with caution. The safeguards:
  - there's no current official injury report (one filed at or after 8 PM the night before the game),
  - a team hasn't filed its report yet, or
  - the line has moved 3+ points **against** the bet since it opened (the market disagrees, which usually means news the model doesn't have yet). Big moves toward the model's side aren't flagged.

  If a caution clears later (for example, the team files its report and the edge is still there), a regular alert follows.
- **"Market agrees" alerts.** When a line moves 3+ points **toward** the model's side since opening, you get a heads-up once per game and market. If the edge is still 3+, it's part of the normal bet alert ("Market agrees: …"). If the move has eaten the edge, it's a low-priority info alert with no bet. These are logged in `state/market_moves.csv`.
- **Line history in every alert.** The 5-minute checks record every line change with the time they first saw it (`state/line_history.csv`), so each alert shows the path, e.g. `225.5 (first seen Fri 11:45 AM) -> 223.5 (Fri 12:10 PM)`. Compare those times with the news below to see whether a move came before or after a report. Since the evening of Oct 30, 2026, current lines come from Action Network, so times are good to about 5 minutes. Earlier rows (and any check where Action Network didn't respond) used ESPN, whose copy can be up to about 15 minutes behind; the `source` column says which. Lines that opened before tracking started say so.
- **Line jump alerts and database.** Every check looks for fast moves: any spread or total that moves **1.5+ points within 60 minutes** is logged in `state/line_jumps.csv` with the before and after lines, how long it had been steady, how fast it moved, hours to tip, whether it moved toward or away from the model, and the injury news posted around it. Moves of **3+ points** also send a **Line jump** notification. The morning run grades each jump (did the line keep moving to the close, did the result land on the side the jump pointed to), and the **Line Jumps** sheet collects them. Settings: `JUMP_WINDOW_MIN`, `JUMP_LOG`, `JUMP_ALERT` in `alert.py`.
- **Latest news in every alert.** Each alert ends with the newest reporter-sourced injury updates for both teams from the last 24 hours (ESPN's injury feed, which picks up beat-writer and insider reports), so you can see what's behind a line move, or that nothing has been reported.
- Every alert, regular or caution, goes into `state/alerts.csv` and the **Alerts** sheet of `NBA_Live_Tracker.xlsx`, and is graded after the game. Regular and caution alerts are graded separately.
- Phone delivery uses [ntfy](https://ntfy.sh). The topic name is stored as the repository secret `NTFY_TOPIC` and never appears in the code.

Settings live at the top of `alert.py`: `THRESHOLD`, `MAX_LINE_MOVE`, and `WINDOW`. `WINDOW = None` (the current setting) means alerts go out at any hour; it can be set to limit alerts to certain hours.

## Logging the bets you actually place

- **From an alert:** tap **Log this bet** on the notification. It opens the form with the game, pick, and line filled in. Fix the line if yours was different, add your odds and stake, and submit.
- **Any other bet:** open the form directly: [Log a bet](https://github.com/JeffreyD24/nba-mixed-model/issues/new?template=log-bet.yml) (bookmark it), or go to **Issues → New issue → Log a bet**.
- A workflow adds it to `state/my_bets.csv`, replies with a confirmation (or what to fix), and closes the issue. Only bets you open are recorded, even though the repo is public.
- The morning run grades each bet at **your** line, odds, and stake, and the **My Bets** sheet shows your record, profit, return, and the model's edge at the lines you got.

## Research database

Each 5-minute check also records market data that can't be recovered later, in `research/`: the full DraftKings
market with prices and moneylines (`research/odds/`), ESPN's matchup predictor, the share of bets and of money on each side (`research/splits/`), lines and prices at nine sportsbooks including Fanatics (`research/books/`), DraftKings player props with opening lines (`research/props/`), in-game lines with the score and clock (`research/live/`), first-half, second-half and 1st-quarter lines and team totals at each book (`research/periods/`), final scores by quarter (`research/linescores.csv`), each player's minutes by quarter for every finished game (`research/minutes/`, rebuilt from play-by-play), every injury note with the time
it was first seen, and the model's number whenever it changes. Rows are written only when something changes.
Every graded pick, alert and logged bet also gets **closing line value** (points your line beat the close by).
Columns, and the questions the data is meant to answer, are in [`research/DATA_DICTIONARY.md`](research/DATA_DICTIONARY.md).

## Files

- `tracker.py`: the morning and evening runs. `alert.py`: the intraday check. `espn.py`: lines. `log_bet.py`: records bets from the form.
- `nba_mixed_model.py`: the mixed model (Henderson's equations, REML variance components, walk-forward).
- `build_report_features.py`, `parse_injury_reports.py`: official injury reports to model features.
- `build_tracker_workbook.py`: builds `NBA_Live_Tracker.xlsx`.
- `data/`: training seasons with features and lines, last season's minutes and player ratings, and how often each injury status means a player sits.
- `state/`: everything the runs build up. `picks_log.csv` holds the locked daily picks, `alerts.csv` the phone alerts, `my_bets.csv` the bets you logged, `injury_reports_2026_27.csv` every parsed report, and `model_YYYY-MM-DD.json` the saved model for today's and tomorrow's games, used by the intraday checks.

## How to read the results, and what to expect

- **The honest test** is the scorecard on the **Summary** sheet: opening lines 3+ points from the locked model number. Judge it only after about 150 bets.
- **Phone alerts fire against later lines,** which are sharper than openers. In every backtest (12 seasons), the model never beat closing lines; its only profit came against opening lines. Expect alerts to land near break-even (52.4% at -110) unless the live data says otherwise.
- **Don't change thresholds mid-season** based on what has been hitting. That turns a fair test into a fitted one.
- **Treat it as a test, not a betting system,** until a full season of live results says otherwise.

## Notes

- Data sources: Kaggle (`eoinamoore/historical-nba-data-and-player-box-scores`) for results and minutes, official NBA injury reports (`ak-static.cms.nba.com`), and ESPN's public odds feed (DraftKings).
- GitHub pauses scheduled workflows in public repos after 60 days without activity. The daily commits from these runs count as activity, so this should not happen during the season.
