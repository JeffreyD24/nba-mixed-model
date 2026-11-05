# Edge statistics (NBA), made 2026-11-05 11:40 ET

## ROI and closing line value with bootstrap ranges

ROI = units won per bet (each bet 1 unit; scorecard NBA/NFL bets at -110). 90% ranges from 10,000 resamples; `by_day` resamples whole days. CLV is in points against DraftKings' close (as logged); Pinnacle price CLV is below.

| source | rule | scope | n | W | L | P | units | roi | roi_lo90 | roi_hi90 | roi_lo90_by_day | roi_hi90_by_day | p_roi_above_0 | clv_n | clv_mean | clv_lo90 | clv_hi90 | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| scorecard | Model 1 open spread 3+ pts | all | 44 | 26 | 18 | 0 | 5.640 | 0.128 | -0.089 | 0.345 | -0.170 | 0.388 | 0.776 | 44 | 1.364 | 0.636 | 2.136 |  |
| scorecard | Model 1 open spread 3+ pts | live only | 13 | 7 | 6 | 0 | 0.360 | 0.028 | -0.413 | 0.469 | -0.318 | 0.432 | 0.606 | 13 | 2.385 | 0.769 | 4.308 | n<30: too few bets to read |
| scorecard | Model 2 open spread 3+ pts | all | 33 | 21 | 12 | 0 | 7.090 | 0.215 | -0.074 | 0.446 | -0.144 | 0.507 | 0.895 | 33 | 1.727 | 0.818 | 2.697 |  |
| scorecard | Model 2 open spread 3+ pts | live only | 8 | 6 | 2 | 0 | 3.450 | 0.432 | -0.045 | 0.909 | -0.045 | 0.718 | 0.888 | 8 | -0.250 | -1.000 | 0.375 | n<30: too few bets to read |
| scorecard | Model 3 open spread 3+ pts | all | 37 | 20 | 17 | 0 | 1.180 | 0.032 | -0.226 | 0.290 | -0.261 | 0.342 | 0.571 | 37 | 1.216 | 0.405 | 2.108 |  |
| scorecard | Model 3 open spread 3+ pts | live only | 7 | 3 | 4 | 0 | -1.270 | -0.182 | -0.727 | 0.364 | -0.236 | -0.045 | 0.343 | 7 | -0.143 | -0.714 | 0.429 | n<30: too few bets to read |
| scorecard | Model 1 open total 3+ pts | all | 43 | 20 | 23 | 0 | -4.820 | -0.112 | -0.334 | 0.110 | -0.336 | 0.105 | 0.222 | 43 | 1.674 | 0.767 | 2.674 |  |
| scorecard | Model 1 open total 3+ pts | live only | 15 | 6 | 9 | 0 | -3.550 | -0.236 | -0.618 | 0.145 | -0.727 | 0.145 | 0.210 | 15 | 2.600 | 0.600 | 4.800 | n<30: too few bets to read |
| scorecard | Model 2 open total 3+ pts | all | 55 | 30 | 25 | 0 | 2.270 | 0.041 | -0.167 | 0.250 | -0.105 | 0.220 | 0.656 | 55 | 1.091 | 0.345 | 1.891 |  |
| scorecard | Model 2 open total 3+ pts | live only | 13 | 6 | 7 | 0 | -1.550 | -0.119 | -0.559 | 0.322 | -0.727 | 0.105 | 0.386 | 13 | 0.692 | -0.615 | 2.077 | n<30: too few bets to read |
| scorecard | Model 3 open total 3+ pts | all | 35 | 18 | 17 | 0 | -0.640 | -0.018 | -0.291 | 0.255 | -0.276 | 0.164 | 0.429 | 35 | 1.343 | 0.286 | 2.514 |  |
| scorecard | Model 3 open total 3+ pts | live only | 6 | 1 | 5 | 0 | -4.090 | -0.682 | -1.000 | -0.045 | -1.000 | -0.364 | 0.009 | 6 | -1.500 | -3.000 | 0.000 | n<30: too few bets to read |
| alerts | alert total caution / DON'T BET | all | 23 | 9 | 14 | 0 | -5.820 | -0.253 | -0.585 | 0.079 | -0.393 | 0.091 | 0.069 | 23 | 0.391 | -0.391 | 1.174 | n<30: too few bets to read |
| alerts | alert spread caution / DON'T BET | all | 11 | 7 | 4 | 0 | 2.360 | 0.215 | -0.306 | 0.562 | 0.041 | 0.591 | 0.829 | 11 | -0.364 | -0.636 | -0.182 | n<30: too few bets to read |
| alerts | alert spread BET | all | 4 | 1 | 3 | 0 | -2.090 | -0.523 | -1.000 | 0.432 | -1.000 | -0.045 | 0.052 | 4 | 0.500 | 0.000 | 1.000 | n<30: too few bets to read |
| alerts | alert total BET | all | 7 | 3 | 4 | 0 | -1.270 | -0.182 | -0.727 | 0.364 | -0.364 | -0.045 | 0.343 | 7 | 1.857 | 1.000 | 2.857 | n<30: too few bets to read |
| my bets | NBA totals v1 | all | 6 | 3 | 3 | 0 | -0.310 | -0.052 | -0.682 | 0.585 | -0.058 | -0.045 | 0.337 | 5 | 0.800 | -0.200 | 1.800 | n<30: too few bets to read |
| my bets | NBA spreads v1 | all | 5 | 2 | 3 | 0 | -1.180 | -0.236 | -1.000 | 0.528 | -1.000 | 0.273 | 0.312 | 5 | 0.200 | -0.400 | 0.800 | n<30: too few bets to read |
| my bets | NBA totals v2 | all | 3 | 2 | 1 | 0 | 0.820 | 0.273 | -0.363 | 0.910 |  |  | 0.739 | 3 | -0.667 | -2.667 | 1.333 | n<30: too few bets to read |
| my bets | NBA totals v4 | all | 1 | 1 | 0 | 0 | 0.930 | 0.930 | 0.930 | 0.930 |  |  | 1.000 | 1 | -2.000 | -2.000 | -2.000 | n<30: too few bets to read |
| my bets | ALL logged bets | all | 15 | 8 | 7 | 0 | 0.260 | 0.017 | -0.366 | 0.401 | -0.328 | 0.277 | 0.605 | 14 | 0.071 | -0.714 | 0.786 | n<30: too few bets to read |


## Calibration: predicted chance vs what happened

### spread_home_cover

`z` is (actual - predicted) in standard errors; |z| above 2 is worth a look, and below 30 bets per bin it is mostly noise.

| set | bin | n | predicted | actual | diff | z | brier | logloss |
|---|---|---|---|---|---|---|---|---|
| spread_home_cover: all games | (-0.001, 0.4] | 21 | 0.318 | 0.333 | 0.016 | 0.154 |  |  |
| spread_home_cover: all games | (0.4, 0.45] | 9 | 0.428 | 0.444 | 0.017 | 0.100 |  |  |
| spread_home_cover: all games | (0.45, 0.5] | 25 | 0.476 | 0.440 | -0.036 | -0.359 |  |  |
| spread_home_cover: all games | (0.5, 0.55] | 16 | 0.525 | 0.562 | 0.037 | 0.299 |  |  |
| spread_home_cover: all games | (0.55, 0.6] | 16 | 0.570 | 0.375 | -0.195 | -1.573 |  |  |
| spread_home_cover: all games | (0.6, 1.0] | 20 | 0.666 | 0.500 | -0.166 | -1.571 |  |  |
| spread_home_cover: all games | ALL | 107 | 0.498 | 0.439 | -0.058 | -1.209 | 0.253 | 0.702 |
| spread_home_cover: live only | (-0.001, 0.4] | 4 | 0.293 | 0.500 | 0.207 | 0.910 |  |  |
| spread_home_cover: live only | (0.4, 0.45] | 4 | 0.420 | 0.500 | 0.080 | 0.324 |  |  |
| spread_home_cover: live only | (0.45, 0.5] | 7 | 0.475 | 0.429 | -0.047 | -0.247 |  |  |
| spread_home_cover: live only | (0.5, 0.55] | 8 | 0.524 | 0.500 | -0.024 | -0.137 |  |  |
| spread_home_cover: live only | (0.55, 0.6] | 6 | 0.571 | 0.500 | -0.071 | -0.351 |  |  |
| spread_home_cover: live only | (0.6, 1.0] | 7 | 0.652 | 0.571 | -0.081 | -0.450 |  |  |
| spread_home_cover: live only | ALL | 36 | 0.510 | 0.500 | -0.010 | -0.121 | 0.256 | 0.707 |


### total_over

`z` is (actual - predicted) in standard errors; |z| above 2 is worth a look, and below 30 bets per bin it is mostly noise.

| set | bin | n | predicted | actual | diff | z | brier | logloss |
|---|---|---|---|---|---|---|---|---|
| total_over: all games | (-0.001, 0.4] | 22 | 0.351 | 0.455 | 0.103 | 1.014 |  |  |
| total_over: all games | (0.4, 0.45] | 23 | 0.429 | 0.478 | 0.050 | 0.481 |  |  |
| total_over: all games | (0.45, 0.5] | 31 | 0.474 | 0.355 | -0.119 | -1.328 |  |  |
| total_over: all games | (0.5, 0.55] | 19 | 0.523 | 0.632 | 0.109 | 0.952 |  |  |
| total_over: all games | (0.55, 0.6] | 10 | 0.570 | 0.400 | -0.170 | -1.088 |  |  |
| total_over: all games | (0.6, 1.0] | 2 | 0.625 | 0.000 | -0.625 | -1.824 |  |  |
| total_over: all games | ALL | 107 | 0.459 | 0.449 | -0.011 | -0.225 | 0.253 | 0.698 |
| total_over: live only | (-0.001, 0.4] | 5 | 0.310 | 0.200 | -0.110 | -0.531 |  |  |
| total_over: live only | (0.4, 0.45] | 8 | 0.425 | 0.750 | 0.325 | 1.857 |  |  |
| total_over: live only | (0.45, 0.5] | 8 | 0.476 | 0.250 | -0.226 | -1.281 |  |  |
| total_over: live only | (0.5, 0.55] | 8 | 0.519 | 0.625 | 0.106 | 0.600 |  |  |
| total_over: live only | (0.55, 0.6] | 5 | 0.576 | 0.400 | -0.176 | -0.796 |  |  |
| total_over: live only | (0.6, 1.0] | 2 | 0.625 | 0.000 | -0.625 | -1.824 |  |  |
| total_over: live only | ALL | 36 | 0.473 | 0.444 | -0.029 | -0.348 | 0.260 | 0.712 |


## CLV against Pinnacle's closing price (games from Nov 2, 2026; live recorder only)

price_clv_pct = fair Pinnacle close x bet decimal odds - 1 (negative = paid the usual vig at the same line; zero or above = beat the close). winpct_pts = fair close chance - break-even chance. points_clv = points better than Pinnacle's closing line.

| source | rule | market | n | points_clv_n | points_clv_mean | points_clv_lo90 | points_clv_hi90 | price_clv_pct_n | price_clv_pct_mean | price_clv_pct_lo90 | price_clv_pct_hi90 | winpct_pts_n | winpct_pts_mean | winpct_pts_lo90 | winpct_pts_hi90 | share_points_positive | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| scorecard | Model 2 open spread 3+ pts | spread | 10 | 10 | 2.500 | -0.550 | 7.350 | 10 | 0.049 | -0.067 | 0.213 | 10 | 2.586 | -3.447 | 11.2 | 0.700 | n<30: too few bets to read |
| scorecard | Model 1 open spread 3+ pts | spread | 11 | 11 | 2.455 | -0.182 | 6.909 | 11 | 0.044 | -0.057 | 0.197 | 11 | 2.306 | -2.979 | 10.2 | 0.636 | n<30: too few bets to read |
| scorecard | Model 3 open spread 3+ pts | spread | 10 | 10 | 2.750 | -0.050 | 7.600 | 10 | 0.060 | -0.048 | 0.229 | 10 | 3.126 | -2.524 | 11.8 | 0.600 | n<30: too few bets to read |
| scorecard | Model 2 open total 3+ pts | total | 13 | 13 | 1.385 | -0.156 | 2.962 | 13 | 0.175 | -0.266 | 0.615 | 13 | 9.158 | -13.9 | 32.2 | 0.615 | n<30: too few bets to read |
| scorecard | Model 1 open total 3+ pts | total | 7 | 7 | -0.429 | -2.286 | 1.571 | 7 | -0.182 | -0.727 | 0.364 | 7 | -9.524 | -38.1 | 19.0 | 0.286 | n<30: too few bets to read |
| scorecard | Model 3 open total 3+ pts | total | 3 | 3 | 0.000 | -2.500 | 2.500 | 3 | -0.364 | -1.000 | 0.273 | 3 | -19.0 | -52.4 | 14.3 | 0.333 | n<30: too few bets to read |
| alerts | alert spread caution / DON'T BET | spread | 17 | 17 | 0.176 | -0.176 | 0.529 | 17 | -0.032 | -0.054 | -0.011 | 17 | -1.691 | -2.841 | -0.546 | 0.471 | n<30: too few bets to read |
| alerts | alert total caution / DON'T BET | total | 22 | 22 | -0.068 | -0.932 | 0.795 | 22 | -0.131 | -0.436 | 0.174 | 22 | -6.853 | -22.8 | 9.108 | 0.409 | n<30: too few bets to read |
| my bets | NBA totals v2 | total | 3 | 3 | -0.500 | -2.500 | 1.500 | 3 | -0.364 | -1.000 | 0.273 | 3 | -18.7 | -52.0 | 14.7 | 0.333 | n<30: too few bets to read |
| my bets | NBA totals v4 | total | 3 | 3 | 0.333 | -1.667 | 2.333 | 3 | 0.600 | 0.282 | 0.918 | 3 | 31.4 | 15.0 | 47.9 | 0.333 | n<30: too few bets to read |
| my bets | ALL logged bets | total | 6 | 6 | -0.083 | -1.750 | 1.583 | 6 | 0.118 | -0.514 | 0.608 | 6 | 6.380 | -26.5 | 31.8 | 0.333 | n<30: too few bets to read |


## By sportsbook (bets logged through `Log a bet`)

Book names are normalized (dk / DraftKings are one book). `(not recorded)` means the form's Sportsbook field was blank.

| book | bets | graded | stake_units | units | roi | roi_lo90 | roi_hi90 | clv_mean | clv_n | first_bet | last_bet | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DraftKings | 14 | 12 | 14.0 | 1.350 | 0.113 | -0.363 | 0.587 | 0.167 | 12 | 2026-10-30 | 2026-11-04 | n<30: too few bets to read |
| FanDuel | 3 | 3 | 3.000 | -1.090 | -0.363 | -1.000 | 0.273 | 1.000 | 3 | 2026-10-30 | 2026-10-30 | n<30: too few bets to read |


### Limit events (`Log a limit` form, state/book_limits.csv)

`bets_logged_at_book_before` counts logged bets at that book up to the end of that day, so a cut can be read against how much was bet and won first.

_no rows yet_

