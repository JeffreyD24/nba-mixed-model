# Edge statistics (NBA), made 2026-11-03 11:30 ET

## ROI and closing line value with bootstrap ranges

ROI = units won per bet (each bet 1 unit; scorecard NBA/NFL bets at -110). 90% ranges from 10,000 resamples; `by_day` resamples whole days. CLV is in points against DraftKings' close (as logged); Pinnacle price CLV is below.

| source | rule | scope | n | W | L | P | units | roi | roi_lo90 | roi_hi90 | roi_lo90_by_day | roi_hi90_by_day | p_roi_above_0 | clv_n | clv_mean | clv_lo90 | clv_hi90 | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| scorecard | Model 1 open spread 3+ pts | all | 39 | 22 | 17 | 0 | 3.000 | 0.077 | -0.168 | 0.322 | -0.246 | 0.358 | 0.688 | 39 | 1.538 | 0.769 | 2.385 |  |
| scorecard | Model 1 open spread 3+ pts | live only | 8 | 3 | 5 | 0 | -2.270 | -0.284 | -0.761 | 0.193 | -0.364 | -0.045 | 0.140 | 8 | 3.875 | 1.500 | 6.500 | n<30: too few bets to read |
| scorecard | Model 2 open spread 3+ pts | all | 29 | 18 | 11 | 0 | 5.360 | 0.185 | -0.078 | 0.448 | -0.222 | 0.516 | 0.832 | 29 | 1.966 | 0.931 | 3.069 | n<30: too few bets to read |
| scorecard | Model 2 open spread 3+ pts | live only | 4 | 3 | 1 | 0 | 1.730 | 0.432 | -0.523 | 0.909 | -1.000 | 0.909 | 0.740 | 4 | -0.500 | -1.500 | 0.500 | n<30: too few bets to read |
| scorecard | Model 3 open spread 3+ pts | all | 32 | 18 | 14 | 0 | 2.360 | 0.074 | -0.224 | 0.372 | -0.253 | 0.400 | 0.699 | 32 | 1.438 | 0.500 | 2.438 |  |
| scorecard | Model 3 open spread 3+ pts | live only | 2 | 1 | 1 | 0 | -0.090 | -0.045 | -1.000 | 0.909 |  |  | 0.254 | 2 | 0.000 | -1.000 | 1.000 | n<30: too few bets to read |
| scorecard | Model 1 open total 3+ pts | all | 38 | 19 | 19 | 0 | -1.730 | -0.045 | -0.297 | 0.206 | -0.270 | 0.167 | 0.435 | 38 | 2.026 | 1.079 | 3.053 |  |
| scorecard | Model 1 open total 3+ pts | live only | 10 | 5 | 5 | 0 | -0.450 | -0.045 | -0.618 | 0.527 | -0.682 | 0.227 | 0.378 | 10 | 4.400 | 2.100 | 7.100 | n<30: too few bets to read |
| scorecard | Model 2 open total 3+ pts | all | 47 | 25 | 22 | 0 | 0.730 | 0.015 | -0.228 | 0.259 | -0.146 | 0.230 | 0.551 | 47 | 1.085 | 0.298 | 1.979 |  |
| scorecard | Model 2 open total 3+ pts | live only | 5 | 1 | 4 | 0 | -3.090 | -0.618 | -1.000 | 0.145 | -1.000 | -0.364 | 0.056 | 5 | 0.000 | -0.400 | 0.400 | n<30: too few bets to read |
| scorecard | Model 3 open total 3+ pts | all | 33 | 18 | 15 | 0 | 1.360 | 0.041 | -0.248 | 0.273 | -0.182 | 0.209 | 0.567 | 33 | 1.576 | 0.545 | 2.758 |  |
| scorecard | Model 3 open total 3+ pts | live only | 4 | 1 | 3 | 0 | -2.090 | -0.523 | -1.000 | 0.432 | -1.000 | -0.045 | 0.051 | 4 | -1.000 | -3.000 | 1.000 | n<30: too few bets to read |
| alerts | alert total caution / DON'T BET | all | 10 | 5 | 5 | 0 | -0.450 | -0.045 | -0.618 | 0.527 | -0.236 | 0.145 | 0.383 | 10 | 1.400 | 0.600 | 2.200 | n<30: too few bets to read |
| alerts | alert spread caution / DON'T BET | all | 4 | 3 | 1 | 0 | 1.730 | 0.432 | -0.045 | 0.909 | -0.045 | 0.909 | 0.740 | 4 | -0.750 | -1.000 | -0.488 | n<30: too few bets to read |
| alerts | alert spread BET | all | 4 | 1 | 3 | 0 | -2.090 | -0.523 | -1.000 | -0.045 | -1.000 | -0.045 | 0.049 | 4 | 0.500 | 0.000 | 1.000 | n<30: too few bets to read |
| alerts | alert total BET | all | 7 | 3 | 4 | 0 | -1.270 | -0.182 | -0.727 | 0.364 | -0.364 | -0.045 | 0.345 | 7 | 1.857 | 1.000 | 2.857 | n<30: too few bets to read |
| my bets | NBA totals v1 | all | 6 | 3 | 3 | 0 | -0.310 | -0.052 | -0.682 | 0.585 | -0.058 | -0.045 | 0.347 | 5 | 0.800 | -0.200 | 1.800 | n<30: too few bets to read |
| my bets | NBA spreads v1 | all | 5 | 2 | 3 | 0 | -1.180 | -0.236 | -1.000 | 0.528 | -1.000 | 0.273 | 0.320 | 5 | 0.200 | -0.400 | 0.800 | n<30: too few bets to read |
| my bets | ALL logged bets | all | 11 | 5 | 6 | 0 | -1.490 | -0.135 | -0.653 | 0.382 | -0.427 | 0.108 | 0.379 | 10 | 0.500 | -0.100 | 1.100 | n<30: too few bets to read |


## Calibration: predicted chance vs what happened

### spread_home_cover

`z` is (actual - predicted) in standard errors; |z| above 2 is worth a look, and below 30 bets per bin it is mostly noise.

| set | bin | n | predicted | actual | diff | z | brier | logloss |
|---|---|---|---|---|---|---|---|---|
| spread_home_cover: all games | (-0.001, 0.4] | 20 | 0.315 | 0.350 | 0.035 | 0.333 |  |  |
| spread_home_cover: all games | (0.4, 0.45] | 7 | 0.431 | 0.429 | -0.003 | -0.014 |  |  |
| spread_home_cover: all games | (0.45, 0.5] | 22 | 0.476 | 0.500 | 0.024 | 0.223 |  |  |
| spread_home_cover: all games | (0.5, 0.55] | 13 | 0.526 | 0.538 | 0.012 | 0.089 |  |  |
| spread_home_cover: all games | (0.55, 0.6] | 13 | 0.569 | 0.385 | -0.184 | -1.343 |  |  |
| spread_home_cover: all games | (0.6, 1.0] | 17 | 0.667 | 0.471 | -0.197 | -1.719 |  |  |
| spread_home_cover: all games | ALL | 92 | 0.493 | 0.446 | -0.048 | -0.914 | 0.256 | 0.708 |
| spread_home_cover: live only | (-0.001, 0.4] | 3 | 0.269 | 0.667 | 0.397 | 1.552 |  |  |
| spread_home_cover: live only | (0.4, 0.45] | 2 | 0.423 | 0.500 | 0.077 | 0.220 |  |  |
| spread_home_cover: live only | (0.45, 0.5] | 4 | 0.477 | 0.750 | 0.273 | 1.092 |  |  |
| spread_home_cover: live only | (0.5, 0.55] | 5 | 0.526 | 0.400 | -0.126 | -0.566 |  |  |
| spread_home_cover: live only | (0.55, 0.6] | 3 | 0.569 | 0.667 | 0.098 | 0.341 |  |  |
| spread_home_cover: live only | (0.6, 1.0] | 4 | 0.648 | 0.500 | -0.148 | -0.620 |  |  |
| spread_home_cover: live only | ALL | 21 | 0.500 | 0.571 | 0.072 | 0.657 | 0.270 | 0.737 |


### total_over

`z` is (actual - predicted) in standard errors; |z| above 2 is worth a look, and below 30 bets per bin it is mostly noise.

| set | bin | n | predicted | actual | diff | z | brier | logloss |
|---|---|---|---|---|---|---|---|---|
| total_over: all games | (-0.001, 0.4] | 21 | 0.351 | 0.476 | 0.125 | 1.203 |  |  |
| total_over: all games | (0.4, 0.45] | 20 | 0.429 | 0.450 | 0.021 | 0.186 |  |  |
| total_over: all games | (0.45, 0.5] | 28 | 0.472 | 0.393 | -0.080 | -0.844 |  |  |
| total_over: all games | (0.5, 0.55] | 14 | 0.528 | 0.571 | 0.044 | 0.328 |  |  |
| total_over: all games | (0.55, 0.6] | 8 | 0.569 | 0.500 | -0.069 | -0.394 |  |  |
| total_over: all games | (0.6, 1.0] | 1 | 0.625 | 0.000 | -0.625 | -1.290 |  |  |
| total_over: all games | ALL | 92 | 0.454 | 0.457 | 0.003 | 0.052 | 0.251 | 0.693 |
| total_over: live only | (-0.001, 0.4] | 4 | 0.297 | 0.250 | -0.047 | -0.207 |  |  |
| total_over: live only | (0.4, 0.45] | 5 | 0.427 | 0.800 | 0.373 | 1.688 |  |  |
| total_over: live only | (0.45, 0.5] | 5 | 0.470 | 0.400 | -0.070 | -0.312 |  |  |
| total_over: live only | (0.5, 0.55] | 3 | 0.537 | 0.333 | -0.204 | -0.708 |  |  |
| total_over: live only | (0.55, 0.6] | 3 | 0.576 | 0.667 | 0.090 | 0.317 |  |  |
| total_over: live only | (0.6, 1.0] | 1 | 0.625 | 0.000 | -0.625 | -1.290 |  |  |
| total_over: live only | ALL | 21 | 0.459 | 0.476 | 0.017 | 0.160 | 0.257 | 0.704 |


## CLV against Pinnacle's closing price (games from Nov 2, 2026; live recorder only)

price_clv_pct = fair Pinnacle close x bet decimal odds - 1 (negative = paid the usual vig at the same line; zero or above = beat the close). winpct_pts = fair close chance - break-even chance. points_clv = points better than Pinnacle's closing line.

| source | rule | market | n | points_clv_n | points_clv_mean | points_clv_lo90 | points_clv_hi90 | price_clv_pct_n | price_clv_pct_mean | price_clv_pct_lo90 | price_clv_pct_hi90 | winpct_pts_n | winpct_pts_mean | winpct_pts_lo90 | winpct_pts_hi90 | share_points_positive | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| scorecard | Model 2 open spread 3+ pts | spread | 4 | 4 | 0.375 | -1.125 | 1.250 | 4 | -0.038 | -0.107 | 0.000 | 4 | -2.003 | -4.076 | 0.019 | 0.750 | n<30: too few bets to read |
| scorecard | Model 1 open spread 3+ pts | spread | 5 | 5 | 0.400 | -0.205 | 1.000 | 5 | -0.040 | -0.069 | -0.014 | 5 | -2.070 | -3.713 | -0.730 | 0.600 | n<30: too few bets to read |
| scorecard | Model 3 open spread 3+ pts | spread | 5 | 5 | 0.100 | -0.500 | 0.800 | 5 | -0.046 | -0.081 | -0.009 | 5 | -2.397 | -4.333 | -0.460 | 0.400 | n<30: too few bets to read |
| scorecard | Model 2 open total 3+ pts | total | 8 | 8 | 1.062 | -1.000 | 3.188 | 8 | -0.045 | -0.523 | 0.432 | 8 | -2.381 | -27.4 | 22.6 | 0.625 | n<30: too few bets to read |
| scorecard | Model 1 open total 3+ pts | total | 5 | 5 | -0.900 | -2.400 | 1.300 | 5 | -0.236 | -1.000 | 0.527 | 5 | -12.4 | -52.4 | 27.6 | 0.200 | n<30: too few bets to read |
| scorecard | Model 3 open total 3+ pts | total | 2 | 2 | -2.250 | -3.000 | -1.500 | 2 | -1.000 | -1.000 | -1.000 | 2 | -52.4 | -52.4 | -52.4 | 0.000 | n<30: too few bets to read |
| alerts | alert spread caution / DON'T BET | spread | 7 | 7 | 0.214 | -0.143 | 0.571 | 7 | -0.046 | -0.066 | -0.029 | 7 | -2.400 | -3.431 | -1.517 | 0.571 | n<30: too few bets to read |
| alerts | alert total caution / DON'T BET | total | 13 | 13 | -0.308 | -1.346 | 0.769 | 13 | -0.119 | -0.559 | 0.322 | 13 | -6.227 | -29.3 | 16.8 | 0.462 | n<30: too few bets to read |
| my bets | NBA totals v2 | total | 3 | 3 | -0.500 | -2.500 | 1.500 | 3 | -0.364 | -1.000 | 0.273 | 3 | -18.7 | -52.0 | 14.7 | 0.333 | n<30: too few bets to read |
| my bets | NBA totals v4 | total | 1 | 1 | -2.500 | -2.500 | -2.500 | 1 | 0.935 | 0.935 | 0.935 | 1 | 48.3 | 48.3 | 48.3 | 0.000 | n<30: too few bets to read |
| my bets | ALL logged bets | total | 4 | 4 | -1.000 | -2.750 | 1.000 | 4 | -0.039 | -1.000 | 0.915 | 4 | -1.918 | -51.5 | 47.8 | 0.250 | n<30: too few bets to read |


## By sportsbook (bets logged through `Log a bet`)

Book names are normalized (dk / DraftKings are one book). `(not recorded)` means the form's Sportsbook field was blank.

| book | bets | graded | stake_units | units | roi | roi_lo90 | roi_hi90 | clv_mean | clv_n | first_bet | last_bet | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DraftKings | 12 | 8 | 12.0 | -0.400 | -0.050 | -0.527 | 0.432 | 0.750 | 8 | 2026-10-30 | 2026-11-02 | n<30: too few bets to read |
| FanDuel | 3 | 3 | 3.000 | -1.090 | -0.363 | -1.000 | 0.273 | 1.000 | 3 | 2026-10-30 | 2026-10-30 | n<30: too few bets to read |


### Limit events (`Log a limit` form, state/book_limits.csv)

`bets_logged_at_book_before` counts logged bets at that book up to the end of that day, so a cut can be read against how much was bet and won first.

_no rows yet_

