# Research database: data dictionary

Everything the tracker records, so it can be analyzed later for edges in how books set and move
lines, and in how the betting public behaves. All times are US Eastern (ET), `YYYY-MM-DD HH:MM`.
Every file is append-only and keyed by `game_id` (the NBA game ID, the same one used in `state/picks_log.csv`),
so the files join on `game_id`.

Snapshots come from the 5-minute alert checks, so their timing is accurate to about 5 minutes, or to
however late GitHub runs a check. A row is written only when something changed, so each row marks the
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

## state/ (tracker records that also feed the research)

| file | what it holds |
|---|---|
| `picks_log.csv` | one row per game: locked model numbers (`pred_margin`, `pred_total`), opening and closing lines, edges, results, grading, and **closing line value** (`open_spread_clv`, `open_total_clv`: points the opening line beat the close by, on the model's side) |
| `line_history.csv` | every spread and total change with the time first seen (from 5-minute checks) |
| `line_jumps.csv` | fast moves (1.5+ points within 60 minutes): before/after, how long the line had been steady, minutes the move took, hours to tip, toward/away from the model, news in the window, then graded (did it keep moving to the close, did the result land on the side of the move) |
| `market_moves.csv` | moves of 3+ points toward the model's side ("Market agrees") |
| `alerts.csv` | every phone alert, including caution alerts with reasons, graded, with `closing_line` and `clv_points` |
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

## Not recorded (yet)
Betting splits (% of bets and % of money on each side). VSIN's free page no longer shows NBA splits (it's for Pro subscribers),
so they aren't scraped.
