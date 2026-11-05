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

## Three models, tracked side by side

Since Oct 30, 2026, every morning and evening run also predicts each game with two more models and locks
their numbers next to Model 1's, from the same night-before injury report:

- **Model 1** (the original): team offense/defense strength + injury reports. **Still the only one that sends phone alerts.**
- **Model 2** (player-based): projected minutes for tonight x each player's rating, plus what each player shows this season.
- **Model 3** (pace x efficiency): possessions and points per possession predicted separately, then multiplied.

All three are graded at the same opening and closing lines in `state/picks_log_models.csv` and on the
**Model Comparison** sheet. Games played before Oct 31 were backfilled from earlier data only and are marked
`backfilled`. The backtest that led to this, with results and takeaways, is in
[`research/model_comparison/`](research/model_comparison/README.md). In short: Model 2 had the most accurate
margins and Model 3 the most accurate totals in both test seasons; none of the three beat closing lines.

If Models 2 or 3 fail in a run, the run logs why and carries on; Model 1's picks and alerts aren't affected.

## How picks are tracked

**The scorecard:** every spread and total whose **opening line** differs from the locked model number by **3+ points** counts as a bet at the opening line, even if the line moved before a bet could be placed. That measures the model itself, not your timing. It's the highlighted rule on the **Summary** sheet.

## Alerts

- **What an alert says:** the model's number, the current DraftKings line (marked "opening line" if it hasn't moved; otherwise it shows where it opened), the edge now, and the edge at the opening line.
- **Rule:** spreads and totals, model vs. the current line, edge of 3+ points. One alert per game per market.
- **Caution alerts.** When the edge is there but a safeguard is triggered, the alert is still sent, titled **CAUTION**, at normal priority, with the reason and a reminder to bet with caution. The safeguards:
  - there's no current official injury report (one filed at or after 8 PM the night before the game),
  - a team hasn't filed its report yet, or
  - the line has moved **half a point or more against** the bet since it opened (`AGAINST_MOVE`). In the 2024-26 backtests,
    bets placed after the line had moved against the model won only about 43% (41-46% in every season and market), while bets
    after it moved toward the model (edge still 3+) won about 56%. Until Oct 31, 2026 this caution needed a 3-point move.

  If a caution clears later (for example, the team files its report and the edge is still there), a regular alert follows, titled **UPDATE**, saying what cleared and how the edge changed since the caution.
- **A verdict at the top of every bet alert** (since Oct 31, 2026): **[BET]**, **[PASS]** or **[OPTIONAL]** in the title and the
  reason on the first line, from the rule the backtests support (2024-26, edge 3+):
  | When the alert goes out | Verdict | Backtest |
  |---|---|---|
  | Line still at the opener, first seen within the last hour (`FRESH_OPEN_MIN`) | BET | 53-55% |
  | Line moved toward the model, 3+ pts of edge left | BET | ~56% |
  | Line moved toward the model, under 3 left | PASS | market caught up |
  | Line moved against the model by 0.5+ | PASS | ~43% |
  | Line still at the opener hours after it posted, or opened before tracking | OPTIONAL | ~49% |
  The alert also repeats the rule, so you can apply it to the line you see in your app.
- **Reminder if you haven't logged the bet:** 30 minutes after an alert (`REMIND_AFTER_MIN`), if no bet is logged for that game
  and market, a **REMINDER** goes out once, before tip, with the line as it is now and an updated verdict (it may now say PASS).
  Alerts whose first verdict was PASS don't get reminders.
- **Key players still undecided.** Every bet alert lists questionable/doubtful/probable players worth 0.75+ model points,
  with how far the model would move if each sits. A low-priority **Key decision pending** heads-up goes out once per player,
  game and status when an undecided player is worth 1.5+ points (margin or total). When a listed player's status changes on a
  new official report, the change is logged with the DraftKings line at that moment (`research/injury_decisions.csv`), and if
  he's worth 1.5+ points an **Injury decision** alert goes out (high priority for Out or Available). The point: the model
  updates as soon as the report posts, so a bet alert right after a decision may be ahead of the line.
- **Reporter news from Bluesky** (since Oct 31, 2026): every minute, `bluesky_watch.py` reads new posts from the ~35 NBA
  reporters in `research/media/bluesky_watch.csv` who post regularly on Bluesky (free, public API). Every post is saved with the
  time it was posted and first seen (`research/bluesky/`), flagged if it's about injuries or lineups, with the players it names.
  When an injury/lineup post names a key player (worth 1.5+ model points) before his game, a **Reporter** alert goes out with the
  post, what he's worth to the line, and an **Open post** button (one alert per player and game per hour). It only recognizes
  players who appear on an official injury report this season. The biggest national breakers (Shams Charania, Chris Haynes) don't
  post on Bluesky; an X watcher for them is planned.
- **Acting on reporter news right away** (since Oct 31, 2026). When a post states a final decision in one sentence ("ruled out",
  "won't play", "resting", "without [player]", or "will play", "cleared to play") with the player's name and no hedge word ("questionable", "expected",
  "likely", "could"...), the watcher saves it to `state/news_overrides.json` and a full check runs at once instead of at the next
  5-minute mark. That check treats the player as Out (or playing) until an official report newer than the post comes out. If the
  news opens a 3+ point edge, the bet alert is titled **NEWS** (even if that game already alerted, when the news flips the side
  or adds 1+ point of edge). For the first 20 minutes after the post its verdict is BET ("bet now if your app still shows this
  number"), or CHECK if the line had already moved 0.5+ against the model. Read the post first: the alert links it.
- **Points in limbo.** Every bet alert and Key decision pending alert has a line adding up every undecided player
  (questionable, doubtful, probable): the range the model's spread and total can still land in once their statuses are final,
  and for a bet alert, the range of its edge (and a warning if it could flip sides). The model's number already counts each
  player's chance of sitting, so "sits" moves it by (1 - chance) x his value and "plays" by -chance x his value.
- **Already bet?** Every bet alert checks the bets you've logged. If you already have a bet on that game and market on the same side, the alert is titled **ALREADY BET**, shows your bet, and comes at normal priority instead of high; if your bet is on the other side, it starts with **YOU BET THE OTHER SIDE**. Bets on the other market of the same game are listed at the end.
- **"Market agrees" alerts.** When a line moves 3+ points **toward** the model's side since opening, you get a heads-up once per game and market. If the edge is still 3+, it's part of the normal bet alert ("Market agrees: …"). If the move has eaten the edge, it's a low-priority info alert with no bet. These are logged in `state/market_moves.csv`.
- **Line history in every alert.** The 5-minute checks record every line change with the time they first saw it (`state/line_history.csv`), so each alert shows the path, e.g. `225.5 (first seen Fri 11:45 AM) -> 223.5 (Fri 12:10 PM)`. Compare those times with the news below to see whether a move came before or after a report. Since the evening of Oct 30, 2026, current lines come from Action Network, so times are good to about 5 minutes. Earlier rows (and any check where Action Network didn't respond) used ESPN, whose copy can be up to about 15 minutes behind; the `source` column says which. Lines that opened before tracking started say so.
- **Line jump alerts and database.** Every check looks for fast moves: any spread or total that moves **1.5+ points within 60 minutes** is logged in `state/line_jumps.csv` with the before and after lines, how long it had been steady, how fast it moved, hours to tip, whether it moved toward or away from the model, and the injury news posted around it. Moves of **3+ points** also send a **Line jump** notification. The morning run grades each jump (did the line keep moving to the close, did the result land on the side the jump pointed to), and the **Line Jumps** sheet collects them. Settings: `JUMP_WINDOW_MIN`, `JUMP_LOG`, `JUMP_ALERT` in `alert.py`.
- **Latest news in every alert.** Each alert ends with the newest reporter-sourced injury updates for both teams from the last 24 hours (ESPN's injury feed, which picks up beat-writer and insider reports), so you can see what's behind a line move, or that nothing has been reported.
- Every alert, regular or caution, goes into `state/alerts.csv` and the **Alerts** sheet of `NBA_Live_Tracker.xlsx`, and is graded after the game. Regular and caution alerts are graded separately.
- Phone delivery uses [ntfy](https://ntfy.sh). The topic name is stored as the repository secret `NTFY_TOPIC` and never appears in the code.

Settings live at the top of `alert.py`: `THRESHOLD`, `MAX_LINE_MOVE`, and `WINDOW`. `WINDOW = None` (the current setting) means alerts go out at any hour; it can be set to limit alerts to certain hours.

## Getting alerts sooner, and placing bets faster (ported from the NHL tracker, Oct 31, 2026)

- **Tomorrow's model is ready from the morning.** DraftKings posts NBA lines around 8:30 PM the night before, but GitHub often
  starts the evening run late (e.g. 11:16 PM on Oct 30). So the morning run now also saves tomorrow's model (`--model-only`:
  nothing is locked). The 5-minute checks use it with the newest official report, so they can alert as soon as lines post.
  The evening run still locks tomorrow's scorecard picks from the 8 PM report.
- **New lines within about a minute:** between 5-minute checks, `opener_watch.py` looks every minute for games where DraftKings
  has just posted a line; a new line triggers a full check at once. In the backtests the edge was gone by the time the line was
  halfway to its close, so the first minutes matter.
- **Bet on DraftKings button:** alerts carry a button that opens DraftKings with that bet on your slip (the link from ESPN).
  If ESPN's copy of the line is behind DraftKings' current line, the button opens the game page instead. You still confirm the bet.

## Player props shadow record (since Nov 5, 2026; paper only)
`props_shadow.py` (workflow `props-shadow.yml`) records FanDuel's NBA player-prop lines every hour from 11 AM to 11 PM ET, and at
11 AM logs paper bets from props v1b (EV 5%+ vs FanDuel) to `state/props_shadow.csv`, graded the next morning with the result and
FanDuel's last pre-tip line (closing-line EV). Why paper: the 2025-26 backtest made money but did not beat the closing line
(`research/props/PROPS_V1_RESULTS_2026-11-05.md`). No alerts. Revisit after ~500 graded paper bets.

## Checking boosts (since Nov 4, 2026)
Open a new issue with the **Check a boost** form (Issues -> New issue). Two ways to use it:
- **Find me the best bet:** pick the book, enter the boost % (and how many legs the token needs, the lowest odds it allows). The reply ranks every
  moneyline, spread and total at that book against Pinnacle's no-vig fair price, with a second table of lower-variance picks at +150 or shorter.
- **Check a bet I picked / an odds boost / an SGP:** type each leg as `description, price, other side's price` (other side optional). The reply
  gives the fair price, the EV, and BET IT / SKIP. Same-game legs get a warning, since the fair price treats them as independent.
The reply arrives as a comment in about a minute and the issue closes itself. Every check is saved to `state/boost_checks.csv`.
Math and the full market plan: `research/MARKET_EXPANSION_PLAYBOOK_2026-11-04.md`. Code: `boost_check.py` (also runs from the command line).

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
- `models_v2.py`: Models 2 and 3. `lineups.py`: projected lineups for Model 2. `models_live.py`: runs, locks and grades them each run.
  `data/models_v2_params.json`: their fitted settings (2021-22 to 2025-26), made by `backtest_v2/fit_live_params.py`.
  `data/last_season_minutes_2025_26.csv`, `data/team_codes.csv`: inputs for the projected lineups. `backtest_v2/`: the backtest scripts as run.
- `data/`: training seasons with features and lines, last season's minutes and player ratings, and how often each injury status means a player sits.
- `state/`: everything the runs build up. `picks_log.csv` holds the locked daily picks (Model 1), `picks_log_models.csv` all three models' locked numbers and grades, `alerts.csv` the phone alerts, `my_bets.csv` the bets you logged, `injury_reports_2026_27.csv` every parsed report, and `model_YYYY-MM-DD.json` the saved model for today's and tomorrow's games, used by the intraday checks.

## How to read the results, and what to expect

- **The honest test** is the scorecard on the **Summary** sheet: opening lines 3+ points from the locked model number. Judge it only after about 150 bets.
- **Phone alerts fire against later lines,** which are sharper than openers. In every backtest (12 seasons), the model never beat closing lines; its only profit came against opening lines. Expect alerts to land near break-even (52.4% at -110) unless the live data says otherwise.
- **Don't change thresholds mid-season** based on what has been hitting. That turns a fair test into a fitted one.
- **Treat it as a test, not a betting system,** until a full season of live results says otherwise.

## Notes

- Data sources: Kaggle (`eoinamoore/historical-nba-data-and-player-box-scores`) for results, minutes, team stats and (this season) referee crews, official NBA injury reports (`ak-static.cms.nba.com`), ESPN's public odds feed (DraftKings) and, for the backtest, ESPN game summaries for past referee crews. Player ratings are EPM from Kaggle (`deocheng/nba-data-1946-2026`).
- GitHub pauses scheduled workflows in public repos after 60 days without activity. The daily commits from these runs count as activity, so this should not happen during the season.

## Polymarket US tracking (paper trades only)

`polymarket.py` (the same file in the NHL, NBA and NFL repos) watches **Polymarket US**, the CFTC-regulated exchange, and
records what the model would do there. **It never trades.** Connecticut has ordered Polymarket to stop offering sports
contracts there, so this builds the record now for use from a state where it's allowed.

**Why an exchange is different:** you trade against other people, not a book, so winners don't get limited, and you can post
your own price (a limit order, no fee) instead of taking the best offer (taker fee ≈ 5% × price × (1 − price) per contract,
about 1.25¢ at 50¢; set in `TAKER_FEE_RATE`).

**What runs:** right after each 5-minute `alert.py` check (`alert_loop.sh`), so it uses the number alert.py just computed:
1. pulls this league's games from Polymarket's public data API (`gateway.polymarket.us`, no key) and matches them to
   `state/model_*.json`;
2. saves the best bid, best offer and depth of every moneyline, spread and total contract to
   `research/polymarket/YYYY-MM-DD.csv` (only when something changed);
3. turns the model's number into a probability for each contract: Model 1's live margin and total plus its misses in the 2024-25 and 2025-26 backtests (`data/poly_residuals.json`, 2,448 games, margin miss sd 14.2, total 18.5), centred on zero so a model total equal to the line is a 50/50 over. P(home covers −5.5) = the share of past misses that would have put the home team ahead by 6+. Its win chances are calibrated (55.2% predicted vs 55.0% actual home wins) but less accurate than the closing line (Brier 0.205 vs 0.199), the same story as the betting results.
4. logs paper trades on the moneyline, spread and total to `state/poly_paper.csv`, one per game, market and model:
   - **taker**: buy at the best offer the first time expected value after the fee is **5%+**;
   - **maker**: a limit bid at the highest price that still has 5% expected value, counted as filled if the best
     offer later falls to it before the game (approximate: ignores who was first in line);
   - each with DraftKings' price on the same bet at that moment (from `research/odds/`), to see which is cheaper.

The **morning run** grades finished trades from Polymarket's settlement prices (`--grade`), adds closing line value (last mid
price before the start minus the price paid, in cents) and rewrites `research/polymarket/REPORT.md`.

**First runs:** this was built from Polymarket US's documentation and tested against mock responses; it had not yet seen real
data. Each day it saves one raw event and one price reply to `research/polymarket/samples/`, and anything it can't read goes
to `research/polymarket/unmatched.csv` (the `line_source` column in the snapshots says whether a spread's sign came from the
side's own text or had to be assumed). Check those after the first day. To pause it, add a repository variable
`POLYMARKET_OFF` = `1` (Settings → Secrets and variables → Actions → Variables); delete it to resume.

Settings at the top of `polymarket.py`: `THRESHOLD`, `PAPER_MARKETS`, `TAKER_FEE_RATE`, `MAKER`, `MIN_DEPTH` (20 contracts).


## Phone alerts: bets only (since Nov 1, 2026)
`BET_ONLY = True` in `alert.py`. Your phone gets only:
- **[BET]** alerts (the rule's verdict is BET), once per game and market. PASS, OPTIONAL and CHECK verdicts and CAUTION
  alerts are logged in `state/alerts.csv` (`sent` = False) but not pushed; if one later becomes a BET, that alert goes out.
- **DON'T BET** follow-ups: a BET alert you haven't logged, before tip, where the model's side flipped, the edge fell under 3,
  or the line moved 0.5+ against it (since the open or since the alert). Once per alert (`stopped_at_et`).
Injury decisions, key decisions pending, reporter posts, market-agrees and line-jump alerts are still detected and saved
in their files; they are just not pushed. The 30-minute reminder was replaced by DON'T BET. Set `BET_ONLY = False` to go back.

## Shooting-luck correction for totals (since Nov 1, 2026)
`nba_luck.py` (morning run) downloads this season's shots from ESPN, rates each by shot quality (`data/shot_quality_model.json`,
fit on 1.09M shots from 2021-22 to 2025-26) and saves each team's season-to-date luck (FG points above or below expected) and
luck allowed in `state/nba_luck.json`. Once both teams have 5+ games, the alerts' model total becomes
model total - 0.5 x (both teams' luck + luck allowed - the league's average so far). Backtest at the opener, edge 3+
(`analysis/FINDINGS.md`): 2024-25 +23.3u vs +16.5u without it, 2025-26 +50.0u vs +46.5u, about 240 more bets. Totals alerts
show the adjustment ("shooting-luck adjustment -4.2"), and `research/model/` logs `model_total_before_luck` and `luck_adjustment`.
- **Prices and bet range in every bet alert (since Nov 1, 2026).** Titles show DraftKings' price, e.g. "Bet MIN -11.5 (-105)".
  The body starts with the verdict and a BET RANGE: from the opening line to the worst number that still has 3+ pts of edge
  ("MIN -10.5 down to -12. Skip if it's worse than -12, or if it moves the other way to MIN -10"). The second half is the rule
  that a 0.5+ move against the model since the open is a PASS. Prices come from Action Network's DraftKings feed
  (`current_home_spread_odds`, `current_away_spread_odds`, `current_over_odds`, `current_under_odds`).


## Edge statistics, sportsbooks and limits
`edge_stats.py` (same file in the NBA, NHL and NFL repos) runs in the morning run and writes `research/edge_stats/REPORT.md` plus CSVs:
- **Bootstrap ranges** (`bootstrap.csv`): ROI and closing line value for every logged rule (scorecard rule at the opening line, BET vs caution alerts, and each model version of your logged bets), with 90% ranges from resampling bets and from resampling whole game days. Rows under 30 bets are flagged.
- **Calibration** (`calibration_*.csv`): predicted probability bins vs what happened, Brier score and log loss. NHL also by price band.
- **Pinnacle closing price** (`pinnacle_clv_*.csv`): price CLV in no-vig terms against Pinnacle's last price before the game, for games from Nov 2, 2026 (when the live recorder started). NBA/NFL bets at a different line than Pinnacle's close are moved to the bet line with the model's backtest misses; NHL keeps points only.
- **Sportsbooks and limits** (`by_book.csv`, `book_limits.csv`): results per book from `state/my_bets.csv` (names normalized by `books.py`) and the limit events you report with the **Log a limit** issue form (label `limit`; create it once at Labels, like `bet`). Each limit is listed with the bets placed at that book before it.
Run by hand with `python edge_stats.py . [--only boot|calib|pinnacle|book]`.
