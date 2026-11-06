# Bet recaps (all sports)

Asked for by Jeffrey on Nov 6, 2026. Made by `betting-goals/ops/recap.py`, run by `.github/workflows/recap.yml` in this repo
(this repo has the phone-notification secret). Each recap is saved here and a short summary with a link goes to your phone.

| Recap | When | Covers | File |
|---|---|---|---|
| Daily | every morning, 4:00 AM ET | games that started from 6 AM yesterday to 4 AM today | `daily/YYYY-MM-DD.md` (the morning's date) |
| Weekly | Monday's 4:00 AM run | the previous Monday-Sunday | `weekly/YYYY-Www.md` (ISO week of that Monday) |
| Monthly | the 1st's 4:00 AM run | the previous calendar month | `monthly/YYYY-MM.md` |

Run one by hand: Actions > "Bet recaps" > Run workflow (pick daily / weekly / monthly and a date), or locally from a folder holding
the four repos: `python betting-goals/ops/recap.py --kind daily --date 2026-11-06 --repos nba-mixed-model nhl-mixed-model nfl-mixed-model --out nba-mixed-model/recaps --espn`.

## What is in each recap

**Daily:** every BET alert for last night's games, by model: game, pick, price, book, edge (points or EV), when it was alerted,
result (W / L / P / void / pending), units and CLV. Then the bets you logged on those games, then every bail-out, DON'T BET and
BACK IN RANGE message sent in the window, then one total line.

**Weekly and monthly:** a summary table, then for every model (and for props every stat: points, rebounds, assists, threes,
receptions, receiving yards) three records, both for the season so far and for the week or month itself, then the full list of
alerts, your bets, and bail-outs / DON'T BETs of the period.

## The three records, in plain words

1. **Every alert (as if you had placed every bet).** Every BET alert the model pushed to your phone this season, under any version,
   1 unit each at the line and price in the alert. If the model alerted the same bet again at a new line (an UPDATE), that counts as
   another bet. Paper picks the model made before it went live (for example NBA props in `state/props_shadow.csv`) are included and
   labeled "paper"; alerts sent under a test-only version are labeled too.
2. **Your bets since the current version went live.** Only the bets you logged (`state/my_bets.csv`), tagged by each repo's own
   `bet_record.py` (the same tagging as `state/record_by_version.csv`), and only those tagged with the version live now (for
   PROVISIONAL models: their own PROVISIONAL record since the current version). Your own price and stake: units = profit / stake.
3. **If you had bet every first alert at the opener since the current version went live.** The first BET alert on each game and
   market since that version's go-live time (`state/bet_versions.csv`), 1 unit at the price in that first alert (the opening price
   the alert was sent on). This is what the model would have made if you never missed or got a worse number.

Each record shows bets, W-L-P, units, ROI (units per graded bet), average CLV and how many are still pending.

## Where each number comes from

| Model | Alerts | CLV measure |
|---|---|---|
| NBA totals / spreads (+ PROVISIONAL 2.5-3 pt totals and injury-news spreads, by the alert's `tier`) | `state/alerts.csv` (sent BET rows) | points vs the closing line (`clv_points`) |
| NBA totals line-movement and blend (PROVISIONAL) | `state/market_models/{movement,blend}_alerts.csv` (pushed) | points |
| NBA props (PROVISIONAL, FanDuel openers) | `state/props_live.csv` (pushed) + paper `props_shadow.csv` | `close_ev`: EV of the alerted price at FanDuel's last pre-tip no-vig line |
| NCAAM stale-line spreads (PROVISIONAL) | `ncaab/state/live_bets.csv` (none sent yet) | points vs our last DraftKings capture |
| NHL moneyline / puck line / overs | nhl-mixed-model `state/alerts.csv` (sent, both-model duplicates removed) | `clv`: EV of the alerted price at the no-vig close |
| NFL totals, spreads (test-only), 2nd-half totals | nfl-mixed-model `state/alerts.csv`, `state/h2_alerts.csv` | points |
| NFL props v2 (receptions, receiving yards; from Nov 6, 2026) | nfl-mixed-model `state/props_live.csv` | `close_ev` |

Bail-outs and DON'T BETs: NBA `state/bailout_alerts.csv`; `stopped_at_et` / `resumed_at_et` in the NBA and NFL alerts logs and the
market-model logs; `reminded_at_et` (DON'T BET) / `resumed_at_et` in the NHL alerts log; `state/props_stop_sent.csv` for props.
Each line shows how the bet it was about turned out.

## Things to know

- **Prices:** the NBA and NFL game alerts logs keep the line but not the price, so those alerts are graded at -110.
  NHL, props, market-model and 2nd-half alerts use their logged price.
- **4 AM grading:** the repos grade last night's games later in the morning (the NBA morning run is 11:41 AM ET), so at 4 AM most
  of last night is still ungraded in the logs. The recap grades those itself from ESPN's final scores and box scores and marks them
  with `*`; the CLV of those rows is blank until the repo's own grade (with the close) is in. Later recaps use the repo's grade.
- **NFL 2nd-half totals** have no row in `bet_versions.csv`, so "went live" is the first 2H BET alert and your 2H bets
  ("before tracking" in `bet_record.csv`) count as its record.
- **NFL props** bets: nfl-mixed-model `bet_record.py` does not tag props yet, so the recap tags a logged prop as "NFL props v2"
  if it was placed after the version went live (from `bet_versions.csv` if a `prop` row is added, else Nov 6, 2026).
- **NBA spreads logged after Nov 5, 11:30 AM** get the NCAAM version from `bet_record.py` (both use market "spread"); the recap
  puts any such bet on NBA teams back on the NBA spreads version.
- The recap only reads the repos; it never changes their files.
