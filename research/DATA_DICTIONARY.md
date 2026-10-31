# Research database: data dictionary

Everything the tracker records, so it can be analyzed later for edges in how books set and move
lines, and in how the betting public behaves. All times are US Eastern (ET), `YYYY-MM-DD HH:MM`.
Every file is append-only and keyed by `game_id` (the NBA game ID, the same one used in `state/picks_log.csv`),
so the files join on `game_id`.

Snapshots come from the 5-minute checks. How fresh each source is depends on how often it refreshes:
Action Network (`splits/`, `books/`) every 30 seconds, so those times are good to about 5 minutes; ESPN's odds and props
feeds (`odds/`, `props/`, and `state/line_history.csv`, `state/line_jumps.csv`) only about every 12 minutes, so those times
can be up to about 15 minutes late. Use `books/` for timing questions about game lines. A row is written only when something changed, so each row marks the
first time a new value was seen.

## research/ (market and information snapshots)

### `research/odds/YYYY-MM-DD.csv`: the full DraftKings market, one file per game date
| column | meaning |
|---|---|
| seen_at_et | when this version of the market was first seen |
| game_id, date, book | game, game date, sportsbook (DraftKings via ESPN) |
| home_spread | current spread, home perspective (-4.5 = home favored by 4.5) |
| home_spread_odds, away_spread_odds | American prices on each side of the spread (-110, -115, ...) |
| total, over_odds, under_odds | current total and its prices |
| home_ml, away_ml | moneylines |
| open_home_spread, open_total, open_home_ml, open_away_ml | DraftKings' opening values |
| espn_event_id | ESPN's game ID (used to fetch the predictor) |

Why it matters: **price moves come before point moves.** A spread going from -110 to -120 with no point change
shows which side the book is taking money on. Spread vs. moneyline vs. total consistency also shows where the
book's own numbers disagree with each other.

### `research/espn_predictor.csv`: ESPN's matchup predictor, about once an hour per game
`seen_at_et, game_id, date, home_win_pct, away_win_pct`. A public model that many casual bettors see. Compare
it with the moneyline's implied probability and with our model, to see whether public-facing projections pull lines.

### `research/news.csv`: every injury and reporter note
`first_seen_et, posted_et, team, note, note_id`. ESPN's feed only keeps each player's latest note, so this
is the only lasting record. `posted_et` is ESPN's timestamp; `first_seen_et` is when the tracker saw it.
Line moves ahead of `posted_et` mean the market knew first.

### `research/model/YYYY-MM-DD.csv`: the model's number through the day
`seen_at_et, game_id, date, home, away, model_margin, model_total, injury_report`, written when the model's number
changes (a new injury report). It shows how much each report moved our number vs. how much it moved the line.

### `research/live/YYYY-MM-DD.csv`: in-game lines (Action Network), every 5-minute check while games are on
`seen_at_et, game_id, date, away, home, status (e.g. "2nd 6:46"), period, clock, away_score, home_score, book, home_spread,
home_spread_odds, away_spread_odds, total, over_odds, under_odds, home_ml, away_ml` for Consensus, DraftKings, FanDuel and Fanatics.
A row is written when the line, price, score or quarter changes. About one snapshot per game every 5 minutes, so it shows how books
adjust to runs and quarters, but not every in-game move.

### `research/periods/YYYY-MM-DD.csv`: halves, 1st quarter and team totals (Action Network), every 5-minute check
One row per game, `period` and book whenever anything changes. `period` is `game`, `firsthalf`, `secondhalf` or `firstquarter`.
Columns: `seen_at_et, game_id, date, away, home, status` (scheduled / inprogress / halftime), `period, book, home_spread,
home_spread_odds, away_spread_odds, total, over_odds, under_odds, home_ml, away_ml, away_team_total, away_tt_over_odds,
away_tt_under_odds, home_team_total, home_tt_over_odds, home_tt_under_odds`. Team totals are each team's own over/under for that
period. Not every book posts every market (blank = not offered). Values outside a sensible range for the period are left blank.

Questions: do books set halves and team totals as simple shares of the game line (often about 49% of the total for the 1st half),
and where does that shortcut miss (pace in 2nd halves, rest, bench-heavy teams)? Do team totals lag when one team's injury news moves the game line?

### `research/linescores.csv`: final score by quarter
`recorded_at_et, game_id, date, away, home, away_q1 ... home_q4` (plus OT columns when there's overtime), `away_final, home_final`.
Written once per finished game, used to grade half, quarter and team-total lines.

### `research/minutes/YYYY-MM-DD.csv`: who played when (minutes by quarter, from ESPN play-by-play)
One row per player per finished game, written once the game is final (this season backfilled from opening night).
| column | meaning |
|---|---|
| game_id, espn_event_id, date, away, home, team, is_home | the game and the player's team |
| athlete_id, player, starter, dnp | ESPN player ID, name, started the game, did not play |
| q1 ... q4 (ot1, ot2 ... in overtime games), h1, h2 | minutes played in each quarter and half |
| total_min, box_min | our total vs. the official box score minutes (box score rounds to whole minutes) |
| diff_vs_box, check_max_diff_min | this player's difference, and the worst difference in the game. Rebuilt from substitutions, so a missing substitution in ESPN's feed shows up here. In the first 68 games, 99% of player rows were within 1 minute; filter on `check_max_diff_min <= 1` for the cleanest games |

Questions: which coaches shorten or lengthen their rotation in second halves, on back-to-backs, in blowouts or close games;
how starters' 4th-quarter minutes change with the score; and whether 2nd-half and team-total lines account for it.
Back-to-backs, rest and home/away come from joining on `game_id` / date with the schedule.

### `research/timeline/YYYY-MM-DD.csv`: every game line from the moment it's posted (Action Network)
Game spread, total, moneyline and prices at DraftKings, FanDuel, Fanatics, Consensus and Action Network's Open, for today and the
next two days, logged whether or not the model has run yet (so the first minutes after a line is posted aren't missed).
`book_changed_utc` is the book's own last-change time (exact); `seen_at_et` is when the check saw it. Keyed by `an_game_id`
(Action Network's ID) plus date, away, home. This is the source for the bet-timing grades.

### `research/minutes_history/season_YYYY.csv`: minutes by quarter for past seasons
Same columns as `research/minutes/` plus `season` (the year it ends), for every regular-season game of 2021-22 through 2025-26
(about 6,150 games), rebuilt from ESPN play-by-play by `backfill_minutes.py` (GitHub workflow "Backfill minutes by quarter").
97-100% of games per season are within a minute of the box score; filter on `check_max_diff_min <= 1`.
Join to `data/training_games.csv` on date + home + away for results, lines, rest and injuries.

### `research/check_log.csv` and `research/errors.csv`: coverage checks
`check_log.csv` has one row per 5-minute check: when it ran, how many seconds the research logging took, and how many rows
each file got. A missing time is a check that didn't run. `errors.csv` records any fetch that failed (which source, which game,
the error), so gaps in the data can be explained rather than mistaken for "nothing changed".

## state/ (tracker records that also feed the research)

| file | what it holds |
|---|---|
| `picks_log.csv` | one row per game: locked model numbers (`pred_margin`, `pred_total`), opening and closing lines, edges, results, grading, and **closing line value** (`open_spread_clv`, `open_total_clv`: points the opening line beat the close by, on the model's side) |
| `line_history.csv` | every spread and total change with the time first seen (from 5-minute checks). `source` says where the line came from: `actionnetwork` (from Oct 30, 2026 evening on; fresh to about 30 seconds) or `espn` (before that, or when Action Network didn't respond; up to about 12 minutes old) |
| `line_jumps.csv` | fast moves (1.5+ points within 60 minutes): before/after, how long the line had been steady, minutes the move took, hours to tip, toward/away from the model, news in the window, then graded (did it keep moving to the close, did the result land on the side of the move) |
| `market_moves.csv` | moves of 3+ points toward the model's side ("Market agrees") |
| `alerts.csv` | every phone alert, including caution alerts with reasons, graded, with `closing_line` and `clv_points` |
| `bet_timing.csv` | each finished game and market graded at 11 time points: the opening line, 15 and 30 minutes and 1, 2, 4 and 8 hours after it, 3 hours, 1 hour and 30 minutes before tip, and the close. Shows the DraftKings line and price at each point, how far it had moved, the model's edge, and two grades: `kept_*` (the side the model liked at the open, bet at that time's line and price) and `fresh_*` (a bet only if the model is still 3+ points off then). `open_time_exact` is true when we saw the line at the moment DraftKings posted it |
| `my_bets.csv` | bets you logged, graded at your line, odds and stake, with `closing_line_your_side` and `clv_points` |
| `injury_reports_2026_27.csv` | every parsed official NBA injury report |
| `model_YYYY-MM-DD.json` | the fitted model state used by the intraday checks |

## Closing line value (CLV)
Points by which a bet's line beat the final line, from the side bet. Positive = you beat the close.
Examples: over 224.5 that closed 226.5 = +2.0; home -3 that closed -4.5 = +1.5.
CLV is the quickest test of a real edge: it shows up in a few hundred bets, long before win rate is reliable.

## Questions this data is meant to answer
- **How books move:** how big is a normal move, at what hours, and how far from tip? Do early moves keep going to the close?
  Do price changes (-110 → -120) predict point changes?
- **Information vs. market:** how often does a line move before the news is posted, and by how much per player (vs. the model's
  injury effect)? Are some teams' or reporters' news priced slowly?
- **Public behavior:** do lines drift toward popular sides (favorites, overs, big-market teams, nationally televised games)
  and then fail to cover? Does ESPN's predictor pull lines?
- **Our timing:** at which hours is our edge vs. the current line largest, and does betting then produce positive CLV?

### `research/splits/YYYY-MM-DD.csv`: where the bets and the money are (Action Network)
| column | meaning |
|---|---|
| seen_at_et, game_id, date, away, home | when first seen, and the game |
| num_bets | how many bets Action Network's sample has on the game (a size and popularity measure) |
| consensus_home_spread, consensus_total | Action Network's consensus line when the split was recorded |
| spread_home_bets_pct, spread_home_money_pct | % of spread **bets** (tickets) and % of spread **money** on the home team (away = 100 minus) |
| over_bets_pct, over_money_pct | % of total bets and money on the over |
| home_ml_bets_pct, home_ml_money_pct | % of moneyline bets and money on the home team |

How to read it: **bets % shows the crowd; money % shows the dollars.** When money % is well above bets %
(for example 35% of bets but 60% of money), fewer, bigger bets are on that side, which usually means sharper
bettors. When bets % is high but the line moves the other way ("reverse line movement"), books are siding
against the public. The splits come from Action Network's sample of sportsbooks, not the whole market, and
are the same at every book.

### `research/books/YYYY-MM-DD.csv`: lines and prices at each sportsbook
`seen_at_et, game_id, date, away, home, book, home_spread, home_spread_odds, away_spread_odds, total, over_odds, under_odds, home_ml, away_ml`
for Consensus, Open (Action Network's opening line), DraftKings, FanDuel, BetRivers, BetMGM, bet365, Caesars and Fanatics.
Shows which book moves first, which ones lag (soft lines to bet into), and how much the books disagree.
Totals under 150 (a few books post period or team totals there) are left blank.

### `research/props/YYYY-MM-DD.csv`: player prop over/unders (DraftKings, via ESPN), every 5-minute check
| column | meaning |
|---|---|
| seen_at_et, game_id, date | when this line/price was first seen, and the game |
| market | Total Points, Total Rebounds, Total Assists, Total 3-Point Field Goals, Total Steals, Total Blocks, and combos (Points and Rebounds, Points, Rebounds, and Assists, ...) |
| athlete_id, player | ESPN player ID and name (`research/props_athletes.csv` has position and ESPN team ID) |
| side | over or under. ESPN lists each pair over-first without labeling it; checked against DraftKings' milestone prices (21+ points = over 20.5), the order matched 55 of 57 times. Recheck against results once games are graded. |
| line, odds | current line and American price for that side |
| open_line, open_odds | DraftKings' opening line and price |
| book_updated | when DraftKings last changed it (ESPN's timestamp, UTC) |

### `research/props/YYYY-MM-DD_other.csv`: everything else DraftKings posts, every 2 hours and once more within 40 minutes of a tip
Milestones (10+, 15+, 20+ points ...), first basket and first team scorer, double-doubles, team totals and team 3s,
and quarter and half spreads, totals and moneylines. Same columns as above; `side` is `line|n` because one player can have
many thresholds. `team_ref` is ESPN's team ID for team props. For milestones, `open_line`/`open_odds` are DraftKings' first posted
values for that slot and aren't reliable.

Why props: books post thousands of these a night, so they get much less attention than spreads, and they're set
from minutes and usage projections that news (a starter ruled out) changes quickly. The questions: how fast do prop lines react
to injury news vs. the game line, do overs on popular players get shaded (priced above fair), and can a minutes-based player model
beat the opening prop number.

Size: the full set is about 1.3 MB per snapshot, so these files are the largest in the repo. Prop rows are written only when a line
or price changes.
