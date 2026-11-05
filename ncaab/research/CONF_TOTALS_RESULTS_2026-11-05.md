# NCAAM conference-game totals: results (Nov 5, 2026)

Pre-registration: `ncaab/research/CONF_TOTALS_PREREG_2026-11-05.md`. Code `ncaab/conf_totals_test.py`; output `ncaab/research/conf_totals_output.txt`.

## Pre-registered test (unseen 2021-22 + 2022-23, at the consensus close): PASS by the letter
370 bets, 209-161 (56.5%), **+29.0u**; 2021-22 +12.7u, 2022-23 +16.3u.

## Decision: NOT live. TEST record on 2026-27 instead
Same rule, same grading (consensus close), on 2023-26: **1,033 bets 49.0%, -67.0u, every season negative.**
| Season | Overs 6+ | Unders 6+ |
|---|---|---|
| 2021-22 | 164 bets 58.5% +19.3u | 60 bets 46.7% -6.5u |
| 2022-23 | 116 bets 60.3% +17.6u | 30 bets 50.0% -1.4u |
| 2023-24 | 203 bets 46.8% -21.6u | 44 bets 43.2% -7.7u |
| 2024-25 | 262 bets 51.1% -6.2u | 36 bets 41.7% -7.4u |
| 2025-26 | 436 bets 50.0% -19.8u | 52 bets 48.1% -4.3u |
Across all five seasons the rule is about -38u. The edge existed (conference overs 2021-23) and has been gone for three seasons
while the number of bets grew. The +14.6u lead that started this was a different rule (games picked by distance from the Open,
graded at the DK close), not the closing-line rule.
The pre-registration's hole: it checked only the unseen seasons, not whether the closing-line version held on the seasons where
the idea was found. Same lesson as the derivatives test: next pre-registrations also state the rule's record on already-seen
seasons graded the same way. Decided by Claude under the standing permission; nothing went live, so no Fable check was needed.

## Leads from this (descriptive)
- The model's totals lean **over** more each season (6+ overs: 164 -> 436 bets a season). Model 1 likely runs high as scoring
  levels shift; Model 2 should let the league scoring level move within a season (time-varying mu) and test whether that alone
  explains the old edge disappearing.
- Non-conference Nov-Dec 6+ totals lose in every view (-23.5u 2021-23): never bet early-season non-conference totals off this model.

The 2026-27 TEST record (`ncaab/state/test_record.md`) now also grades "conference total (vs DK close)" daily.

## Why it faded (descriptive, D-I games, vs consensus close)
| Season | Line minus result, Jan-Apr | Model minus line, Jan-Apr | Model minus result, Jan-Apr | Avg total |
|---|---|---|---|---|
| 2021-22 | -1.22 | +0.93 | -0.29 | 140.1 |
| 2022-23 | -1.73 | +0.58 | -1.15 | 141.5 |
| 2023-24 | -0.68 | +0.85 | +0.17 | 145.3 |
| 2024-25 | -0.84 | +1.24 | +0.40 | 145.7 |
| 2025-26 | -0.57 | +1.95 | +1.38 | 149.4 |
In 2021-23 the closing totals in conference play ran 1.2-1.7 pts too low and the model's overs caught it. The market has mostly
fixed that, while the model drifted above actual results as scoring rose ~9 pts in five years (rule/pace changes). Model 2 idea:
let the scoring level move within the season (recency weight on mu only), pre-registered for 2026-27 data.
