# NBA 1st-quarter lines from who actually starts — results (Nov 5, 2026)

Pre-registration: `research/derivatives/STARTERS_1Q_PREREG_2026-11-05.md` (pushed first, commit efcdbd0).
Script `analysis/starters_1q.py`, output `analysis/starters_1q_output.txt`, per-game rows `analysis/starters_1q_games.csv.gz`.
186,619 stints 2021-26, 1,030 players; 3,556 games with DraftKings' 1Q close and the real starting fives (fit 2023-24: 1,227; test 2,329).

## Result: no edge. Both markets fail the written rule.
| | 1Q spread | 1Q total |
|---|---|---|
| Squared-error gain vs DK close (test) [90%] | −0.007 [−0.067, +0.050] | **−0.138** [−0.251, −0.022] (worse than the line) |
| Calibration slope on 2023-24 (1 = gap fully real) | 0.08 | −0.10 |
| Bets at the 1.0-pt rule | 0 | 0 |
| Biggest 10% of raw gaps, bet the gap's side (descriptive) | 231 games, 51.5% | 233 games, 50.6% |
| 1Q MSE: DK close / starters' model / both | 67.9 / 69.5 / 67.9 | 64.4 / 68.4 / 64.6 |

- The slope of 0.08 means that by the time of the 1Q close, DraftKings has already priced about 92% of whatever the starting five
  tells us (or the starting five tells us nothing new). Shrunk that hard, almost no game gets a 1-point edge, so no bets fire.
- The ridge penalty picked was the largest in the written grid (1,000 stint-minutes) and still trailed the line on 2023-24; a larger
  penalty would only shrink the ratings further toward the line. Not re-tuned (that would be choosing after seeing results).

## Side findings
- "Surprise" starts (any change from the team's previous starting five) happen in 77% of games, so the flag isn't selective;
  no difference in gain either way.
- The 1Q starters' gap barely relates to the 1st-half cover (corr +0.002) and slightly to the full-game cover at the DK close
  (corr +0.038, n 2,327, about p 0.07). Noticed, not tested; logged in TRENDS so it can be checked later, not bet.

## Takeaways
1. **DraftKings' 1Q close already knows who starts.** The derivation from the full-game line looked mechanical in the opener test,
   but by tip the close has absorbed lineups. Whatever edge exists in 1Q lines would have to be taken *before* lineups are public, which
   means predicting starters, not reading them.
2. **Quarter/half markets are closed out for now** (opener-scaling test Nov 4, starters test today). The effort moves to player props,
   where the market has hundreds of thinly-watched lines instead of one heavily derived one.
3. Lineup ratings (RAPM-style ridge on stints) now exist as a reusable piece; the props model can use them for minutes and usage context.
