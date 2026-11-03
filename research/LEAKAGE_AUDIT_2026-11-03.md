# Leakage audit of the NBA, NHL and NFL models (Nov 3, 2026)

Same file in all three repos (research/LEAKAGE_AUDIT_2026-11-03.md). Done by Opus as an independent check, per research/HANDOFF_TO_OPUS.md.
Question asked of every backtest that supports a live rule: **could the bettor have known this at the moment the bet is graded?**
Nothing in the live systems was changed by this audit.

## Summary
| # | Finding | Sport | Kind | Measured effect |
|---|---|---|---|---|
| 1 | Totals v2 graded at the week-early opener but uses **actual game-time wind and temperature** | NFL | leak | **+43.1u → +21.3u** without weather (truth in between) |
| 2 | Walk-forward uses the **night before's results**, which the opener (posted ~8:30 PM that night) can't know | NBA | leak | live totals +145.3u → +129.7u; Model 1 totals +16.5u → +7.7u; spreads unchanged |
| 3 | "Opening" injury snapshot is a **game-day report** (1 PM / 11 AM) in ~9% of games | NBA | leak | not measured; small |
| 4 | **Pinnacle filters** graded at DraftKings' opening price, but Pinnacle posts 3-12 hours later | NBA, NHL | timing | NHL: +64.5u betting every open vs +36.2u waiting for Pinnacle (documented Nov 2) |
| 5 | Filters and thresholds **chosen on the same seasons that report their record** | all | selection | see below; some confirmed elsewhere, some not |
| 6 | Small in-sample pieces (p_miss rates, calibration, shrink weights fit on test seasons) | all | minor | small |

Checked and clean: NBA player ratings use last season's EPM (`season − 1`) and minutes from earlier games only; NHL backtests refit the
xG model per split and use the one-day lag; NHL expected goalie = share of earlier starts; NFL scorecard uses the early number from
last week's reports (the fake 54.4% was already fixed Oct 30); no live model is trained on closing lines.

## 1. NFL totals v2: game-time weather against the opening total (biggest)
`nba-mixed-model analysis/nfl_weather_leak_test.py` (output `nfl_weather_leak_test_output.txt`). Reproduces the documented record exactly, then
refits both components without weather. DK openers 2020-25, edge 2+, weeks 5-14:
| Version | Bets | Win % | Units | Avg line move toward the bet |
|---|---|---|---|---|
| game-time weather (as backtested) | 375 | 58.4% | +43.1u | +1.32 pts |
| no weather at all | 288 | 56.2% | **+21.3u** | +1.30 pts |
| weather in team model only | 301 | 58.5% | +35.0u | +1.40 pts |
| weather in player model only | 362 | 57.5% | +35.1u | +1.35 pts |
- The leak channel is real: in outdoor games with 15+ mph wind, the total fell **2.0 points** from open to close (0.5 in calm games).
  The market learns the wind during the week; a backtest that already knows it at the open is crediting itself with that move.
- The truth for a bet placed at the opener with a 6-day forecast is somewhere between +21u and +43u, probably nearer the low end
  (6-day wind forecasts are weak).
- **The good news:** with no weather at all the rule still wins (56.2%) and its bets still beat the close by 1.3 points on average.
  That line movement is the strongest evidence in the NFL work that the totals signal is real.
- The STRONGER SIGN note ("an under in wind 10+") and the WEAKER SIGN cold note were also measured with game-time weather. At the opener
  they describe information the bettor doesn't have yet.
- The live alert itself is fine: it uses the forecast available at alert time (weather.py).

## 2. NBA: one night of results the opener couldn't know
`nba-mixed-model analysis/lag_leak_test.py` (output `lag_leak_test_output.txt`). NBA openers post around 8:30 PM ET the night before, while that
night's games are being played, and the live tracker locks tomorrow's model in the morning. The backtests used `date < game date`, i.e.
they also knew the night before. The NHL fixed exactly this on Oct 30 (`lag_days=1`); the NBA never did.
| DK openers 2023-24..2025-26, edge 3+ | Knows the night before | Live morning lock |
|---|---|---|
| Model 1 spreads | 1,209 bets 50.8% −36.8u | 1,226 bets 50.8% −36.6u |
| Model 1 totals | 1,549 bets 52.9% +16.5u | 1,552 bets 52.6% +7.7u |
| Live totals (Model 1 + luck + last-10 form) | 1,571 bets 57.2% +145.3u | 1,556 bets 56.7% **+129.7u** |
The reproduction matches the documented live totals (+147.1u). The totals edge survives the fix; it is about 1 unit per 100 bets smaller.

## 3. NBA: game-day injury reports used as "opening" information
`build_report_features.py` uses the 8 PM night-before report, else falls back to the 11 AM game-day report. In the data, 1-1.4% of games use
the 11 AM report and another ~8% use a 1 PM game-day report: about **9% of games** get injury news posted after the opener.
Fix (not applied): fall back to the team's report from its previous game (already done when no report exists at all).

## 4. Pinnacle filters graded at the opener
NHL "skip when Pinnacle's first moneyline disagrees" and NBA "PASS when Pinnacle's first spread is on the other side": Pinnacle posts ~3 h
(NHL) and 5-12 h (NBA) after DraftKings. The supporting records (NHL agrees +138.1u; NBA opened toward us +42.8u) grade the bet at DraftKings'
**opening** price but filter it on information from hours later. You can't do both: either bet at the open (no filter yet) or wait (worse
price). The NHL already measured it honestly once: betting every open +64.5u, waiting and betting only when Pinnacle agrees +36.2u.
In practice the filter only helps bets you haven't placed yet. Re-grade both rules at the price available when Pinnacle first posts.

## 5. Rules chosen on the seasons that report them
Not leakage in the strict sense, but the quoted records are best-case. Status after looking for independent evidence:
| Rule | Chosen on | Independent evidence | Verdict |
|---|---|---|---|
| NHL overs only, EV 6%+ | 2021-26 | SBR 2016-22 holdout: +16.5%/bet, closing total rose on 33.5% of picks vs 10.9% of all games (backtests/OOS_SBR_RESULTS.md) | **confirmed** |
| NHL no bet on 2nd night of a back-to-back | 2021-26 (−28% ROI) | SBR holdout: −1.8% ROI, worst CLV (−2.8%); betting against them +7.0% | direction confirmed, much weaker |
| NHL moneyline 55/45 blend, EV 4%+ | 2021-26, EV bar chosen there | SBR holdout: +1.2%/bet, CLV −1.2% (team-only model, no goalies) | not confirmed |
| NBA totals luck + last-10 form | weights fit out of season; window chosen among ~8 | lag-fixed record still +129.7u | holds |
| NBA spreads: Oct-Jan, no home dogs | 2023-26 | 12 older seasons (closing lines): home dogs lose 47.4%/46.2% | home dogs confirmed |
| NBA spreads: Feb-Apr traps | 2023-26 | older seasons: tanking confirmed; playoff-spot trap **not** (49.1% vs 49.2%) | partly confirmed |
| NFL totals v2: weeks 5-14, edge 2+, stronger/weaker notes | 2020-25 | 2026 weeks 5-8 ~20-12; weather part leaks (above) | real but overstated |

## 6. Minor
- NBA `p_miss` by status is measured on 2022-25, which includes the test seasons. Population rates; small effect.
- NHL/NBA calibration is fit on the last training season's walk-forward predictions made with effects estimated on that season (repo design).
- NBA market-shrink weights (0.25 / 0.39) were fit on the same two seasons they describe; fine as a first estimate, re-test on 2026-27.

## Suggested fixes (none applied; your call)
1. NBA backtests: add the one-day lag (as `analysis/lag_leak_test.py` does) to every script that grades at the opener, and use the previous
   game's report instead of the game-day fallback. Quote +130u, not +147u, for live totals.
2. NFL totals v2: quote the record as "+21u to +43u depending on how much weather is knowable at the open". Keep recording forecasts
   (research/weather/forecasts.csv); after a season, re-test with the forecast that existed at the opener. Open-Meteo also has an archive of
   past forecasts that may allow testing 2022-25 properly now (not tried).
3. Re-grade the Pinnacle filters at the price available when Pinnacle first posts.
4. Keep the new-version-new-record rule: none of these change Model 1.

## Personal note and takeaways
- **No fatal leak.** Every live money rule still shows an edge after its leak is removed: NBA totals (+130u), NFL totals v2 (+21u, with
  bets that beat the close), NHL overs (confirmed on six unseen seasons). The sky didn't fall.
- **The pattern to watch:** each leak was information that arrives between the opener and the game (last night's results, game-day injury
  reports, game-day weather, Pinnacle's later price). The models' edge is at the opener, so anything timestamped after the opener is the
  thing most likely to flatter a backtest. Ask "when was this known?" for every new feature.
- **The NFL weather one matters most for expectations:** about half of the backtested v2 profit was weather the opener couldn't know.
  Expect something closer to 55-56% than 58%.
