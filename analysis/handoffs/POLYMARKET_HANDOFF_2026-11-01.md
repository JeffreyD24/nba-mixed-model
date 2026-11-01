# Polymarket US tracker handoff (Nov 1, 2026)

## Goal
Start tracking Polymarket US now, as paper trades only, and build a record of how the NHL, NBA and NFL models would do on an exchange. Trade for real after moving to a state where it's allowed.

## Legal status (as of Nov 1, 2026; check again before trading)
- Polymarket US is the CFTC-regulated app.
- Connecticut ordered it to stop offering sports contracts in September 2026, after an earlier cease-and-desist in December 2025.
- The CFTC sued Connecticut in April 2026, arguing federal law overrides the state.
- Published lists of blocked states disagree. Check the destination state when the move happens.
- Reading Polymarket's public price data is fine from Connecticut. The tracker never trades.

## Why an exchange matters
- You trade against other people, not a sportsbook, so winning accounts don't get limited.
- You can post your own price with a limit order. Makers pay no fee.
- Takers pay about 5% × price × (1 − price) per contract, which is about 1.25¢ at 50¢.

## What was built
**Commits** (pushed to main):
- `JeffreyD24/nhl-mixed-model` at `a74ef2c`
- `JeffreyD24/nba-mixed-model` at `c4b464f`
- `JeffreyD24/nfl-mixed-model` at `581aee0`

**Files:**
- **`polymarket.py`:** one identical file in all three repos. It detects the sport from the model file it finds.
- **`alert_loop.sh`:** runs `python polymarket.py .` right after `alert.py` every 5 minutes, so it uses the live model number. It also saves `state/poly_paper.csv` and `state/poly_last.json`.
- **`morning.yml`:** a new step runs `python polymarket.py . --grade` before the save step. NBA and NFL now also save `research/polymarket`.
- **`alerts.yml`:** passes `POLYMARKET_OFF` from the repo variables. Setting it to `1` pauses the tracker.
- **NBA and NFL only, `data/poly_residuals.json`:** the model's backtest misses, used to turn margins and totals into probabilities.
- **Docs:** a new section in each `README.md` and in `research/DATA_DICTIONARY.md`.

## How each check works
1. **Find games.** Pull this league's events from the public API at `https://gateway.polymarket.us`; no key is needed. The calls are `/v1/events` filtered by sports and start time, then `/v1/markets/{slug}/bbo` for prices. Match each event to `state/model_*.json` by team names and start time.
2. **Save prices.** Write the best bid, best offer and depth of every moneyline, spread and total contract to `research/polymarket/YYYY-MM-DD.csv`. A row is written only when something changed.
3. **Turn the model into probabilities:**
   - **NHL:** the repo's own Poisson model (`market_probs`, `over_prob`) on the live expected goals. Both the shot (xg) and goals models run, each with its own trades. Only the ±1.5 puck line is priced.
   - **NBA:** Model 1's live margin and total, plus its misses from the 2024-25 and 2025-26 backtests (2,448 games). Margin miss sd is 14.2 and total miss sd is 18.5.
   - **NFL:** the live margin and total, plus misses from the last four backtest seasons (1,139 games). Margin miss sd is 12.8 and total miss sd is 13.3. Using real results means key numbers like 3 and 7 are built in.
   - **How the misses are used:** they are centred on zero, so a model total equal to the line is a 50/50 over. Probabilities come straight from the share of past misses, with no bell curve.
   - **Calibration:** predicted home-win rates match actual ones (55.2% vs 55.0% NBA, 55.6% vs 54.7% NFL). Accuracy is worse than the closing line (Brier 0.205 vs 0.199 NBA, 0.222 vs 0.210 NFL), consistent with any edge being at the opening price.
4. **Log paper trades** to `state/poly_paper.csv`, one per game, market and model:
   - **Taker:** buy at the best offer the first time expected value after the fee is at least 6% for NHL or 5% for NBA and NFL.
   - **Maker:** a limit bid at the highest price that still has that expected value. It counts as filled if the best offer later drops to it before the game. This ignores queue position, so it is approximate.
   - **Markets:** NHL trades moneyline and puck line only; totals are saved but not traded, matching the alert rule. NBA and NFL trade moneyline, spread and total.
   - **Comparison:** each trade records DraftKings' price on the same bet at that moment, taken from `research/odds/`.
   - **Depth:** at least 20 contracts are needed at a price (`MIN_DEPTH`).
5. **Grade each morning.** Use Polymarket's settlement price (`/v1/markets/{slug}/settlement`). Add closing line value, which is the last mid price before the start minus the price paid, in cents. Then rewrite `research/polymarket/REPORT.md` with:
   - units, return and average closing line value
   - the share of limit orders that filled
   - how often Polymarket was cheaper than DraftKings

## Settings (top of `polymarket.py`)
`THRESHOLD`, `PAPER_MARKETS`, `TAKER_FEE_RATE`, `MAKER_FEE_RATE`, `MAKER`, `MIN_DEPTH`, `HOURS_BEFORE`, `TOTAL_RANGE`, `SPREAD_MAX`.

Other commands:
- `--residuals` rebuilds the NBA or NFL miss file.
- `--force` runs a check even when `POLYMARKET_OFF` is set.

## Testing status
- Built from Polymarket US's documentation and tested end to end in all three sports against mock responses in the documented format. Matching, both NHL models, taker and maker trades, fills, grading, closing line value and the report all worked.
- **Not yet seen real data.** Claude's workspace can't reach Polymarket, but GitHub Actions can.
- A network failure exits cleanly and does not interrupt the alert loop.

## Check after the first live day
- **`research/polymarket/unmatched.csv`:** events or contracts that couldn't be read, with the reason.
- **The `line_source` column in the price files:** `side description` is reliable. `market line` means the spread's sign was assumed and needs checking.
- **`research/polymarket/samples/`:** one raw event and one price reply per day, to confirm field names. These fields are assumed from the docs, not yet confirmed:
  - `teams[].name`, `teams[].abbreviation`, `teams[].id`
  - `marketSides[].long`, `marketSides[].teamId`, `marketSides[].description`
  - `sportsMarketType` and `line`
  - prices as `{"value": "0.43"}` objects
- **Whether the events list accepts `startTimeMin` and `startTimeMax`.** The code falls back to filtering itself if not.

## Questions the data should answer
- Do Polymarket prices lag DraftKings after goalie or injury news? If so, the alert pipeline is the edge.
- Do limit orders at the model's price get filled, and are the filled ones winners or the result of adverse selection?
- Is Polymarket cheaper than DraftKings for the same bets?
- Does the opening-price edge seen at sportsbooks also exist on Polymarket?
