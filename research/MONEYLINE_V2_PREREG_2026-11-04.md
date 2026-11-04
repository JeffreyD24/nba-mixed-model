# NBA moneyline v2 — pre-registration (Nov 4, 2026)

Written and pushed **before any result is run.** Nothing here goes live without Jeffrey's approval and a Fable review.

## Why a new model
The first moneyline test (analysis/nba_moneyline.py) turned the spread model's predicted margin into a win chance. It barely beat
nothing: Brier 0.2055 vs DraftKings' opener 0.2007, and when blended with the opener the best weight on our model was only
0.11-0.26. Raw results swung -39 / +45 / -3 units by season. The useful signals were all *filters* (away teams, +150 or shorter,
Pinnacle's first price agreeing, line moving our way), not the model itself. A moneyline is a win/lose question, so v2 models
win probability directly and uses information the spread model ignores (who actually plays, especially stars).

## Data and season split (same seasons idea as the other sports)
| Role | Seasons | Prices | What it is used for |
|---|---|---|---|
| Build | 2011-12 .. 2018-19 (SBR archive) | closing moneyline only | fit every model and its market weight |
| Choose | 2021-22, 2022-23 (Odds API) | DraftKings open + close, Pinnacle | pick the model and the EV bar |
| Lockbox | 2023-24, 2024-25, 2025-26 | DraftKings open + close, Pinnacle | opened once, for the chosen model only |

COVID seasons 2019-20 and 2020-21 excluded (standing decision). Caveat: the first moneyline test and the spread rules were chosen on
2023-26, so the old filters (away only, +150 or shorter, no home underdogs) **cannot be confirmed** on the lockbox; they are reported
there as information only. Their fair test is the build + choose seasons.

## Timing (no look-ahead)
Features use only games through the day before (DK NBA openers post ~24 h before tip). Availability uses who missed the previous game
(data/external/nba_box/missed_value.csv) and injury reports only where the report time is before the opener.

## Candidate models (all output P(home win))
- **M0 — old baseline:** live spread margin -> logistic (as in nba_moneyline.py), refit on build seasons.
- **M1 — win-probability mixed model:** logistic GLMM; fixed effects home court, rest / back-to-back, travel, altitude; team
  random effects with time decay. Sports state-space idea: Glickman & Stern (1998), JASA 93:25-35.
- **M2 — player-availability model:** team strength = sum over expected players of (prior rating x expected minutes), with
  star absences entering directly. Paper: Deshpande & Jensen (2016), J. Quantitative Analysis in Sports 12(2):51-72 (player impact
  on win probability).
- **M3 — Elo with margin of victory:** cheap benchmark. Paper: Hvattum & Arntzen (2010), Int. J. Forecasting 26(3):460-470.
- **M4 — stack:** average of the logits of M1-M3, weights fit on build seasons.

## Market blend (the gate every model must pass)
`p = logistic( logit(market no-vig) + w x (logit(model) - logit(market)) )`, w fit on build seasons.
Paper on reading probabilities from odds: Strumbelj (2014), Int. J. Forecasting 30(4):934-943.
**A model passes only if** on the choose seasons (a) w > 0 with its 95% interval above 0 and (b) the blend's log loss beats the
DraftKings opener alone. A model that fails is reported and dropped, however its units look.

## Betting rule tested
Bet the side with the larger blended EV at the DraftKings opener when EV >= X, X chosen on the choose seasons from {2, 3, 4, 6}%.
1 unit per bet at the real price. Secondary rows (reported, not chosen on): price +150 or shorter; away only; no home underdogs;
Pinnacle's first price agreeing.

## Measures (order of importance)
1. **CLV:** our side's no-vig win chance at DK's close minus at the price we bet (percentage points). Success needs mean CLV > 0
   on the lockbox.
2. **Units:** positive overall and in at least 2 of 3 lockbox seasons. Expect about +/-35u of luck per season on moneylines.
3. Log loss, Brier and accuracy vs the opener, reported alongside.

## What happens with the answer
- Passes: propose as a PROVISIONAL rule (new version row in state/bet_versions.csv), test-tracked first, alerts only after approval.
- Fails: the moneyline stays test-only (state/ml_test.csv), and anything learned (e.g. star absences) gets tried on spreads/totals.
