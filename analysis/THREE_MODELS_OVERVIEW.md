# NBA, NHL and NFL mixed models: overview and shared lessons

Written Oct 31, 2026, to bring the NHL and NFL projects into this one. Sources: the three GitHub repos
(`JeffreyD24/nba-mixed-model`, `nhl-mixed-model`, `nfl-mixed-model`) and the full handoffs written in the NHL and NFL
projects (`analysis/handoffs/NHL_HANDOFF_2026-10-31.md`, `analysis/handoffs/NFL_HANDOFF_2026-10-31.md`).

## The three trackers at a glance

| | NBA | NHL | NFL |
|---|---|---|---|
| Model | Mixed model on points: team offense/defense, home, back-to-backs, official injury reports × player EPM. Models 2 (player-based lineups) and 3 (pace × efficiency) run alongside since Oct 30 | Two models: goals (team offense/defense + **starting goalie** random effects) and shot-based **xG** (chance creation/prevention, finishing, goalie goals saved above expected) | Mixed model on points: team offense/defense, home, short week, bye, indoor, neutral site, injury reports × snap share (QBs separate) |
| Markets | spread, total | moneyline, puck line (totals tested, left out) | spread, total |
| Bet rule (scorecard) | opening line 3+ pts from the locked model | expected value 6%+ at the opening price | opening line 3+ pts from the **early** number |
| Backtest vs opening lines | profitable: ~53-55% (Model 2 spreads, Model 3 totals strongest) | profitable: shot model +9.0% per bet, goals model +3.4% (2024-26) | **no edge**: 49.8% spreads and totals (2023-25) |
| Backtest vs closing lines | never profitable (12 seasons) | lost every season | lost |
| Status | tracking test | tracking test, both models alert | tracking test and research database; nothing in the backtests says it will win |

## Lessons that held in more than one sport

1. **Nothing beats the closing line.** All three models are less accurate than closing prices. Any edge is in the opening
   number, before the market adjusts.
2. **The edge disappears fast once the line moves.**
   - NHL: shot model +9.0% per bet at the open, +2.3% halfway to the close, -2.2% at the close.
   - NBA (tested Oct 31): at edge 3+, opening line 53-55% winners; halfway to the close 48%; close 48-49%. Raising the bar
     (edge 4, 5, 6+) didn't rescue halfway bets.
   - The direction matters most. NBA: bets after the line moved **against** the model won 43% (41-46% in every season and
     market); after it moved **toward** the model (edge still 3+) 56%. NFL: 47-49% vs 52-55%. Even a half-point move against
     dropped NBA bets to 45%.
   - Applied: NBA and NFL now send a CAUTION alert after any half-point move against the bet (was 3 points). NHL already
     raises its bar from 6% to 9% EV once a price moves.
3. **Speed to the opener matters.** NHL built a one-minute "opener watch" and locks tomorrow's model in the morning because
   DraftKings posts lines long before the evening run. NBA has the same timing problem (lines post ~8:30 PM the night before;
   the evening run often starts after 11 PM). Applied to NBA on Oct 31: tomorrow's model is saved in the morning, plus the
   one-minute opener watch and the Bet on DraftKings button.
4. **Information the opener didn't have flatters a backtest.** NFL: grading the Friday-injury-report number against the
   opener looked like 54.4%; the honest early-week number was 49.8%. NBA: scoring openers with the pre-tip report
   flattered every model (52.4% → 54.3%). NHL: locks with only results known when DraftKings opens (one-day lag). Rule for
   all three: the scorecard number may only use what was known when the opening line posted.
5. **Bigger model edges don't win more often** (NBA, Oct 31): 3-4 pts 53.8%, 8+ pts 53.4%. Bet flat. The NHL goals model
   also overrates long-shot underdogs (+150 or longer): said 40%, won 30-35%.
6. **Players matter more than team averages.** NBA Model 2 (lineups × player ratings) had the most accurate margins; NHL's
   biggest gain was knowing the starting goalie (+41-49 units at opening prices with the confirmed goalie). The edge is in
   absorbing player news faster than the line. This is why the NBA tracker now warns about undecided key players and logs
   how the line moves when each status is decided.
7. **The same rule, reached independently in two sports: a weaker edge is only worth taking at the opening price.** NHL
   (decided Oct 31): goals-model bets at +150 or longer alert only while the price is within 1.5 win-% points of the open
   ("OPENING PRICE ONLY"), because they made +2.1% per bet at the open but lost at later prices.
8. **Why the NBA model does better than the NFL one** (NFL handoff): softer NBA openers (lines gain ~0.3 pts of accuracy by the
   close vs ~0.1 in the NFL), the NBA model is about as accurate as the opener (NFL: 0.1-0.5 pts worse), 82 vs 17 games per team,
   and NBA injury reports often come out before the opener.
9. **Things that didn't help:** referees (NBA totals), in-season updating of home and back-to-back effects (NHL), QB-quality
   and EPA models (NFL), team-specific or coach-specific back-to-back rotation habits (NBA), first/second-half lines (NFL),
   hockey totals.
10. **Judge by closing line value early.** Positive CLV while losing usually means bad luck; negative CLV means a real problem
   (NHL Oct 31 cold-stretch review: shot model +1.0% CLV while losing, goals model -3.6%).

## What was ported on Oct 31, 2026

| From → to | What |
|---|---|
| NHL → NBA | morning save of tomorrow's model; one-minute opener watch; Bet on DraftKings button (falls back to the game page if ESPN's copy of the line is stale) |
| NBA → NFL, NHL | UPDATE alerts that say why a follow-up alert came after a caution; ALREADY BET / YOU BET THE OTHER SIDE checks against logged bets |
| NBA test → NBA, NFL | caution after any half-point line move against the bet |
| New (NBA) | key-player warnings: undecided players worth 0.75+ model points listed in every bet alert; "Key decision pending" (1.5+ pts) and "Injury decision" alerts; `research/injury_decisions.csv` logs every status change with the line at that moment |

## Next steps worth doing

- **NFL key players:** the same pending/decision alerts for QBs and other high-snap players (Wednesday-Friday practice reports).
- **NHL key players:** goalie confirmations already drive cautions; add the line-at-confirmation log so goalie news can be
  measured the way NBA injury decisions now are.
- **Bet-timing grades for NHL and NFL:** the NBA tracker grades every bet at 11 time points from open to close; the same
  table would show how long each sport's edge lasts live.
- **Player-impact table (NBA):** after a few weeks of `injury_decisions.csv`, compare each player's actual line move with
  the model's estimate. The model's values come from last season's EPM and minutes and look low for stars (e.g. ~2 points
  for Stephen Curry), so expect the market to move more for stars.
- **Cold-stretch review for NBA:** the NHL `season_diagnostic.py` approach (season-only models, loss breakdowns by price
  band, favorite/underdog, home/away) is worth porting before the first NBA losing streak, not after.

## Ideas from the other projects that could carry over to the NBA

- **Market-informed priors** (NFL idea): start each season from preseason win totals or power ratings instead of only last
  season's effects. Most useful early in the season, when the NBA model's team effects are weakest.
- **Halftime overreaction** (NFL idea): do second-half lines overreact to the first-half score? The NBA tracker now records
  in-game and second-half lines at several books (`research/live/`, `research/periods/`), so this can be tested after a few weeks.
- **Faster player news** (NHL lesson: knowing the goalie was the biggest gain): for the NBA, the equivalent is getting
  injury decisions before the line moves, which the new key-player alerts and `injury_decisions.csv` start to measure.
- **Backtest at real intraday prices** (NHL plan): once a few weeks of line history are saved, grade alerts at the price that
  was actually available when they fired.

## Shared practices (all three projects)

- Never change thresholds mid-season based on what's hitting; test ideas on past seasons first, then forward-test with a fixed rule.
- Judge after a few hundred rule bets (NBA ~150 per market, NHL ~300 per model, NFL more than one season); use CLV for an earlier read.
- Bets are placed by hand (sportsbook terms ban automated betting); small stakes on alerts to test whether bets can be placed
  before lines move; logging mistakes are expected and should be excluded when results are calculated.
- Each repo's bot commits every 5 minutes, so always pull before pushing.
