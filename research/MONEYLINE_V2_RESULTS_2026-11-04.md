# NBA moneyline v2 — results (Nov 4, 2026)

Pre-registration: `MONEYLINE_V2_PREREG_2026-11-04.md` (commits 59034e1 and 67b4a91, both pushed before any result).
Full tables: `analysis/ml_v2_output.md`. Code: `analysis/ml_v2_data.py`, `ml_v2_features.py`, `ml_v2_eval.py`.

## Verdict: NOT passed. No model earns weight against the DraftKings opener. Lockbox (2023-26) left sealed.

| Model | Log loss build (model / SBR close) | w build | w choose vs DK open (95% CI) | Log loss choose: blend / DK open / model | Gate |
|---|---|---|---|---|---|
| M1 win-prob mixed model (tau 120 d) | 0.6045 / 0.5868 | 0.00 | 0.10 (-0.11 to 0.30) | 0.6231 / 0.6231 / 0.6386 | fail |
| M2 M1 + availability | 0.6043 / 0.5868 | 0.00 | 0.14 (-0.07 to 0.34) | 0.6231 / 0.6231 / 0.6368 | fail |
| M3 Elo (MOV) | 0.6058 / 0.5868 | 0.04 | 0.01 (-0.19 to 0.21) | 0.6231 / 0.6231 / 0.6426 | fail |
| M4 stack | 0.6037 / 0.5868 | 0.01 | 0.10 (-0.11 to 0.31) | 0.6230 / 0.6231 / 0.6377 | fail |

Because the build-season weight on every model is ~0, the blend equals the market, so no bet clears even a 2% EV bar
(0-2 bets on the choose seasons). Per the pre-registration, the lockbox is not used.

What the pieces did (M2 fit, logit per unit): home court +0.35; back-to-back home -0.11, away +0.19 (opponent's b2b helps);
altitude +0.14; rest difference +0.06 per day; travel ~0; missing-player value home -0.03, away +0.07 per point (right sign, small).

## Exploratory (added after the results, not part of the test): the line moves toward the models
`analysis/ml_v2_explore_linemove.py`, choose seasons. Regressing DK's open-to-close move on the model-vs-open disagreement (logit):
M1 slope +0.095 (t +7.0), M2 +0.105 (t +7.6), M3 +0.066 (t +4.8), M4 +0.098 (t +6.9). Models correlate 0.87-0.88 with the opener.
Missing-player value vs the move: -0.011 (t -2.7): absences we knew about two nights earlier keep moving the line after the open.

## Personal note and takeaways
- **The models know something, just not enough.** The closing line drifts about 10% of the way toward them, the same size as the
  fitted weight (0.10-0.14) and the old moneyline model (0.11-0.26) and NBA spreads (0.15). A 10% lean is a fraction of a win-%
  point, and the moneyline vig is ~4.5%, so it can't pay. A better public-data team model will not fix this; the opener already
  has ~90% of it.
- **Where an NBA moneyline edge could come from is timing, not modelling:** news that arrives after the open (injury reports,
  lineups). The availability result agrees with the spreads step 3a finding: the market is still moving on absences after the open.
  The next attempt should model the *line move* (open to close) from news, and bet before the move, rather than model the game.
- **Lockbox untouched**, so 2023-26 is still a clean test for that next attempt.
- **Nothing live changes.** The moneyline stays test-only (`state/ml_test.csv`, away +150 or shorter under the spread rules).
- Carry-over to other markets: the "does the model earn weight against the price" gate is a general efficiency test; a model can
  move in the right direction (positive CLV slope) and still be worthless after costs.
