# Three-model comparison (backtest, Oct 30 2026)

All three models were trained and tested on **the same games and seasons**:

- **Test:** train 2021-22 to 2024-25, test every 2025-26 game (1,224).
- **Check:** train 2021-22 to 2023-24, test every 2024-25 game (1,224).

Six games that had no box score were dropped from all three models. Every prediction uses only
information available before the game. Bets against **closing lines** use the last injury report at least
an hour before tip (plus referee crews for Model 3). Bets against **opening lines** use the 8 PM report from
the night before and no referees, since crews are announced the morning of the game.

| | What it does |
|---|---|
| **Model 1** (original) | Team offense and defense strength, home court, back-to-backs, injury report players weighted by minutes x last season's EPM. |
| **Model 2** (player-based) | Builds each team from its players: projected minutes for tonight (recent minutes x chance he plays, from the injury report) x last season's EPM, plus a player-by-player adjustment learned during the season, plus a team adjustment. |
| **Model 3** (pace x efficiency) | Predicts possessions (pace) and points per 100 possessions separately, then multiplies them. Team pace, offense and defense, injuries, back-to-backs, and referee crews. |

## Accuracy (average miss, in points)

| | Margin 2025-26 | Margin 2024-25 | Total 2025-26 | Total 2024-25 |
|---|---|---|---|---|
| Model 1 | 11.24 | 10.92 | 14.91 | 14.64 |
| Model 2 | **11.07** | **10.66** | 15.00 | 14.62 |
| Model 3 | 11.32 | 10.93 | **14.81** | **14.46** |
| Closing line | 10.83 | 10.55 | 14.61 | 14.11 |

Same-game comparisons against Model 1 (`accuracy_tests.csv`):
- **Model 2 margins are better in both seasons**, by 0.17 and 0.26 points (z = -2.7 and -3.4). That's very unlikely to be luck.
- **Model 3 totals are better in both seasons**, by 0.10 and 0.18 points (z = -1.7 and -2.1). Fairly convincing.
- Model 3's margins are slightly worse than Model 1's in 2025-26 (+0.08), which makes sense: pace doesn't change who wins.

## Betting at the opening line, edge 3+ (win %, bets) — break-even is 52.4%

| | Spread 2025-26 | Spread 2024-25 | Total 2025-26 | Total 2024-25 |
|---|---|---|---|---|
| Model 1 | 52.4% (387) | 54.3% (418) | 55.9% (417) | 53.5% (492) |
| Model 2 | 52.8% (316) | **60.6% (317)** | 54.1% (455) | 54.7% (523) |
| Model 3 | 51.3% (425) | 53.7% (434) | **56.6% (380)** | **56.0% (473)** |

Bigger edges (edge 5+):

| | Spread 2025-26 | Spread 2024-25 | Total 2025-26 | Total 2024-25 |
|---|---|---|---|---|
| Model 1 | 50.8% (132) | 56.4% (156) | 60.6% (155) | 53.4% (236) |
| Model 2 | **60.0% (80)** | **65.9% (91)** | 57.1% (189) | 57.3% (248) |
| Model 3 | 51.8% (143) | 54.4% (149) | **60.0% (130)** | **59.5% (200)** |

## Betting at the closing line, edge 3+

| | Spread 2025-26 | Spread 2024-25 | Total 2025-26 | Total 2024-25 |
|---|---|---|---|---|
| Model 1 | 46.0% | 52.2% | 50.2% | 46.9% |
| Model 2 | 50.2% | 53.6% | 49.5% | 45.8% |
| Model 3 | 47.6% | 49.9% | 51.4% | 50.2% |

None of the three beats closing lines.

## Referees (Model 3)

Referee crews move Model 3's total by about 1 point per game on average (largest single referee effect
about 1.5 points), but they didn't make totals more accurate: 14.81 vs 14.84 without them in 2025-26, and
14.46 vs 14.43 in 2024-25 (`referee_ablation.csv`). So far, referees aren't worth betting on.

## Takeaways and advice

- **Model 2 is the best spread model.** It's the only one that's clearly more accurate on margins in both
  seasons, and its opening-line spread record improves as the edge grows in both seasons (52.8% → 60.0%
  and 60.6% → 65.9%), which is what a real edge should look like. The 2025-26 number at edge 3+ is still
  only break-even, so this isn't proven.
- **Model 3 is the best totals model.** It's more accurate on totals in both seasons and has the most
  consistent opening-line totals record (56.6% and 56.0%, about 60% at edge 5+).
- **A natural pairing is Model 2 for spreads and Model 3 for totals.** I would not switch the phone alerts
  yet. Let all three run side by side this season and decide after about 150 opening-line bets per model
  and market, judging by win rate **and** closing line value.
- **Nothing beats closing lines.** The edge, if real, is in getting numbers before the market adjusts.
- **Sample size:** with 300–450 bets, one season's win rate has a margin of error of about ±5 points
  (95%). That's why every number above is shown for two seasons. Only patterns that hold in both count.
- **Testing many versions inflates luck.** Three models x two markets x several edge levels is a lot of
  comparisons. The live 2026-27 results are the only fully fair test.

## Notes

- Model 1's opening-line numbers here use the night-before report for the predicted game, the same way the
  live tracker works. Scoring opening lines with the later pre-tip report flatters every model a little
  (Model 1's 2025-26 spreads: 54.3% with the pre-tip report vs 52.4% with the night-before report).
- Model 2 found that once lineups are modeled, the extra team adjustments shrink to almost zero: the
  players explain the teams. The lineup coefficients were 0.83 (own offense) and -1.25 (opponent defense)
  points per point of lineup EPM.
- Model 2's variance components were estimated from the two most recent training seasons to keep the
  fitting time reasonable, then all effects were solved on every training season.
- Files: `comparison_table.csv` (edges 3/4/5, both lines), `accuracy_tests.csv`, `referee_ablation.csv`,
  and `predictions_2025_26.csv` / `predictions_2024_25.csv` with every game's lines and all three models'
  numbers. Scripts are in `backtest_v2/`.
