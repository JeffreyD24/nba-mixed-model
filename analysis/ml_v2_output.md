# NBA moneyline v2 results

## Step A: choose tau for M1 on build seasons (leave-one-season-out log loss)
  tau  30: log loss 0.6119
  tau  60: log loss 0.6086
  tau 120: log loss 0.6045
  -> tau = 120 days

M2 coefficients (all build seasons): const +0.346, rd_120 +0.233, b2b_h -0.109, b2b_a +0.185, travel_h +0.010, travel_a -0.007, alt_home +0.136, rest_d +0.059, mv_h -0.029, mv_a +0.067
M4 stack weights: const -0.01, lg_M1 -0.27, lg_M2 +0.87, lg_M3 +0.41

## Step B: market blend. w fit on build vs SBR close; gate on choose seasons vs the DraftKings opener
| Model | log loss build (model / close) | w build | w choose (95% CI) vs DK open | log loss choose: blend / DK open / model | Gate |
|---|---|---|---|---|---|
| M1 win-prob mixed model | 0.6045 / 0.5868 | -0.00 | 0.10 (-0.11 to 0.30) | 0.6231 / 0.6231 / 0.6386 | fail |
| M2 M1 + availability | 0.6043 / 0.5868 | -0.00 | 0.14 (-0.07 to 0.34) | 0.6231 / 0.6231 / 0.6368 | fail |
| M3 Elo (MOV) | 0.6058 / 0.5868 | 0.04 | 0.01 (-0.19 to 0.21) | 0.6231 / 0.6231 / 0.6426 | fail |
| M4 stack | 0.6037 / 0.5868 | 0.01 | 0.10 (-0.11 to 0.31) | 0.6230 / 0.6231 / 0.6377 | fail |

## Step C: bets at the DraftKings opener on the choose seasons (2021-22, 2022-23); CLV = no-vig win-% points, close minus open
| Model, EV bar | Bets | CLV | Units | Win % | By season (units / CLV) |
|---|---|---|---|---|---|
| M1 win-prob mixed model, EV 2%+ | 0 | | | | |
| M1 win-prob mixed model, EV 3%+ | 0 | | | | |
| M1 win-prob mixed model, EV 4%+ | 0 | | | | |
| M1 win-prob mixed model, EV 6%+ | 0 | | | | |
| M2 M1 + availability, EV 2%+ | 0 | | | | |
| M2 M1 + availability, EV 3%+ | 0 | | | | |
| M2 M1 + availability, EV 4%+ | 0 | | | | |
| M2 M1 + availability, EV 6%+ | 0 | | | | |
| M3 Elo (MOV), EV 2%+ | 2 | +2.12 | -2.0u (-100.0%) | 0.0% | 22:-1.0u/-2.98 23:-1.0u/+7.22 |
| M3 Elo (MOV), EV 3%+ | 1 | +7.22 | -1.0u (-100.0%) | 0.0% | 23:-1.0u/+7.22 |
| M3 Elo (MOV), EV 4%+ | 1 | +7.22 | -1.0u (-100.0%) | 0.0% | 23:-1.0u/+7.22 |
| M3 Elo (MOV), EV 6%+ | 0 | | | | |
| M4 stack, EV 2%+ | 0 | | | | |
| M4 stack, EV 3%+ | 0 | | | | |
| M4 stack, EV 4%+ | 0 | | | | |
| M4 stack, EV 6%+ | 0 | | | | |

**No model passed the gate. Per the pre-registration the lockbox is not used to pick anything.**

## Secondary rows on the choose seasons (information only; filters were found on 2023-26)
M3 Elo (MOV), EV 4%+:
| Filter | Bets | CLV | Units | Win % | By season |
|---|---|---|---|---|---|
| all | 1 | +7.22 | -1.0u (-100.0%) | 0.0% | 23:-1.0u/+7.22 |
| price +150 or shorter | 0 | | | | |
| away only | 0 | | | | |
| no home underdogs | 0 | | | | |
| Pinnacle first price agrees | 1 | +7.22 | -1.0u (-100.0%) | 0.0% | 23:-1.0u/+7.22 |
| away, +150 or shorter | 0 | | | | |

