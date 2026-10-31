# NHL mixed model: full handoff (through 2026-10-31, 2:45 PM ET)

Everything from the NHL project chat ("NBA mixed model replication for NHL", Oct 30-31 2026), its project docs and saved notes, condensed. The code, data and full backtest tables live in the repo: **github.com/JeffreyD24/nhl-mixed-model** (public). Sister repo: github.com/JeffreyD24/nba-mixed-model.

## 1. Goal and working approach (Jeffrey's decisions)
- Replicate the NBA mixed model and everything around it (daily GitHub runs, ntfy phone alerts, bet log, research database, Excel workbook) for the NHL.
- Build several models that have shown past profit, keep recording data for all of them, and run them **side by side** with labeled alerts; decide later which to trust (nothing switches automatically). Cares most about results at **opening lines**.
- Places small bets on alerts to test whether bets can be placed before the line moves; expects some logging mistakes and wants them excluded or handled when results are calculated.
- Never change thresholds mid-season based on what's hitting; test ideas on backtests first. Judge after ~300 rule bets per model.

## 2. Live system (branch `main`)
**Two models, separate locked picks, both send alerts:**

| | Goals model `nhl_mixed_model.py` | Shot / xG model `nhl_xg_model.py` |
|---|---|---|
| Response | regulation goals (periods 1-3) | expected goals (xG) per shot: distance, angle, power play, rebound, shot type, score state (coefficients fit once on 2021-22..2025-26 → `data/xg_model.json`) |
| Random effects | team offense, team defense, starting goalie | team chance creation, chance prevention, finishing, goalie goals saved above expected |
| Picks file | `state/picks_log.csv` | `state/picks_log_xg.csv` |

**Common machinery:** Henderson MME + REML (three variance components), effects carried across seasons via rho × last season's effect, recency weighting (half-life tuned on last training season), walk-forward with no lookahead. Fixed effects: home ice, back-to-back (offense and defense), missing regular skaters (expected TOI × last season's shrunk points/60 above replacement). Goalie before announcement = share of last 10 starts, yesterday's starter down-weighted on back-to-backs (same goalie starts both nights only ~14%). Expected goals → Poisson score matrix + OT/SO (home wins ~51-52%) → win %, win by 2+, total distribution → logistic calibration (empty-net goals make 2-goal margins more common than Poisson). Trains on 2021-22..2025-26. Arizona mapped to Utah.

**Information timing (one-day lag):** DraftKings posts NHL lines ~11:20 AM-12:30 PM ET the day before (~31 h ahead), before the prior day's games are played. Since 10/30 both live picks and backtests use results only through two days before the game (`dev/lag_backtest.py`); backfilled goals picks were rebuilt under this rule.

**Schedule:**
- Morning run 10:11 AM EDT / 9:11 AM EST: today's games + `--tomorrow` (locks tomorrow before DraftKings opens), grades results, alerts, bets, line jumps; rebuilds `NHL_Live_Tracker.xlsx`.
- Evening run 9:33 PM EST / 10:33 PM EDT.
- Alert checks every 5 min (`alert_loop.sh`, ~50-min loops); `opener_watch.py` checks every minute for newly posted DraftKings lines and triggers a full check (Action Network fallback if ESPN lags).

**Scorecard rule (both models):** moneyline + puck line, EV ≥ 6% at the **opening** DraftKings price, 1 unit, graded at that price even if it moved. Totals tracked but not in the rule or alerts. EV = model prob × decimal odds − 1.

**Alerts (ntfy, secret `NTFY_TOPIC` set and working):**
- Labeled [Shot model] / [Goals model] / [Both models]; graded separately (`model` column in `state/alerts.csv`).
- Bar: EV ≥ 6% while price is within 1.5 win-% points of open; EV ≥ 9% once moved further or line number changed (`THRESHOLD`, `THRESHOLD_MOVED`, `NEAR_OPEN` in `alert.py`).
- CAUTION alerts: goalies not both confirmed, or moneyline moved 5+ win-% points against the bet. "Market agrees" low-priority alerts (5+ toward). Line jump alerts (logged at 3+ points in 60 min, alerted at 5+ or a full goal on totals).
- Buttons: **Bet on DraftKings** (bet-slip link from ESPN data; not yet tested on phone) and **Log this bet**. Bets are placed by hand: DraftKings' terms ban automated betting.

**Bet logging:** GitHub issue form "Log a bet" → `state/my_bets.csv`, graded at Jeffrey's price/stake with model prob, EV and CLV. Logged so far: OTT @ SJ, Sharks ML +130, $1 (NHL); PHI @ CHA under 215.5 −115, $2.50 (NBA repo). A third bet (a puck line) was cut off in a screenshot and may still need logging.

**Scorecard / comparison:** `state/leaderboard.json`, Models sheet of the workbook (rule bets, units, CLV, alert results, Brier).

**Research data saved (unrecoverable later):** `research/line_moves/` (every price change at 9 books with exact times, saved daily; Action Network keeps ~1 day), `research/odds/` 5-min DraftKings snapshots, `research/goalies.csv` (every probable/confirmed goalie change), ESPN predictor, injury notes, betting splits, multi-book lines, model numbers. Data dictionary: `research/DATA_DICTIONARY.md`.

## 3. Backtests (walk-forward, no lookahead, one-day lag)
- Opening prices exist only for 2024-25 and 2025-26 (Action Network); closing back to 2021-22.
- ML + PL, EV ≥ 6%, both opening-line seasons: **shot +119.0u on 1,295 bets (+9.2%)**; **goals +72.0u on 1,796 (+4.0%)**.
- Halfway between open and close (synthetic): shot +3.8%, goals +0.3%. At closing prices both lose (shot ≈ −2%, goals ≈ −4%). Most of the edge is gone by halfway → bet early. 9% cutoff held up better at halfway (chosen after seeing results; a hint, not a finding).
- Shot model more accurate on moneylines in all 4 test seasons (Brier 0.2311/0.2331/0.2358/0.2452 vs goals 0.2324/0.2359/0.2370/0.2482). Market is more accurate than either.
- Knowing the confirmed goalie/lineup boosted opening-price results a lot (goals ML +41.6u / +49.3u) but not vs closing → the edge is in prices that haven't caught up to goalie news.
- Original goals-model table (before lag fix): 2024-25 ML +16.2u, PL +7.2u; 2025-26 ML +23.1u, PL +13.6u; totals lost both seasons; closing-price results negative every season.
- Files: `backtests/XG_MODEL.md`, `lag_backtests.csv`, `midpoint_prices.csv`, `totals_variants.csv`, `IDEA_TESTS.md`.

## 4. Things tried and rejected
- **Totals fix** (branch `totals-fix`, not merged): in-season adaptive baseline and per-line (5.5/6.5) calibration. Every variant's totals log-loss 0.690-0.699 vs coin flip 0.693 and market 0.688 → no totals skill. The 2025-26 "221 unders" was noise, not a bug. Totals stay out.
- **In-season home-ice / back-to-back updating:** tuning chose "don't update" in 7 of 8 fits. Not adopted.
- **Two-season calibration:** mixed (shot +132.8 vs +119.0 at open, goals worse, both worse at close). Not adopted.
- **Shot model skipping +150 and longer:** hurts (+69.4 vs +119.0); its long shots are calibrated (said 39.9%, won 38.3%, needed 34.6%).
- **Favorites-run monitor:** week-to-week correlation −0.29 over 52 weeks; hot streaks don't persist. Context only.
- Options added to code but **off**.

## 5. Season so far (cold-stretch review, 10/31, 216 games)
- Goals model 68-96, −29.0u, avg CLV −3.6%, Brier 0.2410. Shot model 63-75, −13.7u, CLV **+1.0%** (positive every week since 10/5), Brier 0.2325. DraftKings open 0.2313.
- Losses concentrated in +150..+249 underdogs (goals −15.7u, shot −12.3u; won ~25.5% vs ~35.5% needed). Shot model's favorites −150 and shorter 18-6, +2.5u.
- Favorites beating market (134 vs 124.7 expected, z = 1.3); home teams 57.4% (training 53.7%); both models lean underdog and away. Back-to-back offense −0.32 goals this season vs 0.19 in models. League scoring normal (6.34 G/gm).
- Team ratings are fine (close to season-only fits). The goals-model problem is turning ratings into win chances for lopsided games: it overrates long-shot dogs structurally (all 4 seasons at close: said 39.9%, won 30.4%, needed 34.4%, −141u on 1,126; at open +13.5u on 641).
- Reading: shot model's slump looks like variance (positive CLV); goals model's negative CLV is a real problem.

## 6. Decision made 10/31 (live): goals-model long shots at the opening price only
- Goals-model bets priced **+150 or longer** alert only while the price is within 1.5 win-% points of the opening price (`OPEN_ONLY_LONGSHOTS = {"goals": 150}` in `alert.py`). Once the price moves, no alert.
- Those alerts are titled **OPENING PRICE ONLY** and say the shortest price still worth taking ("bet only at +169 or longer"; the floor is whichever is stricter: near the opening price, or EV still ≥ 6%).
- Why: the goals model's underdog win chances run ~5 points high. Its +150-and-longer bets made +13.5u on 641 at the open (+2.1% per bet, a thin edge) but lost at later prices (halfway and close). Fully skipping them was also tested: open +58.5u on 1,155 vs +72.0u on 1,796 with them.
- Shot-model long shots alert normally (calibrated). Scorecard rule unchanged. `state/alerts.csv` has an `open_only` column to grade these separately.

## 7. Possible next steps
- Third model: player-level ratings from public NHL shift charts (players as random effects, BLUP/ridge on shifts) + DailyFaceoff projected lines.
- Faster goalie news than ESPN (beat reporters / morning skate); goalie knowledge is the biggest gain in backtests.
- After a few weeks of `line_moves`, backtest at real intraday prices (when an alert would have fired).
- Possible totals model built on shot volume/pace (separate project).
- Check whether the Bet on DraftKings button fills the slip on a phone.
- Review models after ~200-300 rule bets each.

## 8. Background notes
- **How sharp models get ahead:** NHL EDGE puck/player tracking and Sportlogiq pass/zone data (paid), line-by-line matchup models from shift charts + projected lines, paid fast injury/goalie news and reporter-watching bots, automated betting at the open, using the market as a baseline. Free and reachable for us: shift-chart player model, projected lines, faster goalie news.
- **Automation/legal:** US books (DraftKings, FanDuel) ban scripts/bots; sharp US bettors use semi-automation (computer flags, human taps). Pinnacle/Betfair APIs aren't legally available in the US. Kalshi has a trading API, but Connecticut ordered Kalshi, Robinhood and Crypto.com to stop sports contracts in Dec 2025 (status may have changed; not legal advice). Opening limits are low and books limit winning accounts.

## 9. Rebuilding data
`python build_history.py .` → `python build_shots.py .` (53 MB, gitignored) → `python make_training.py .` → `python make_xg_inputs.py .`. The bot commits state every 5 min, so always pull before pushing.
