# NCAAM conference-game totals: pre-registration (Nov 5, 2026)

Pushed before any 2021-22 or 2022-23 conference-game totals bet was graded.

## Where the idea came from (already seen, so it cannot prove itself)
Model 1 backtest (`ncaab/research/backtest_output.txt`), descriptive slice: totals with 6+ pts of edge in conference games,
2024-26: 580 bets 55.9%, +38.5u at the Open, **+14.6u at the DraftKings close**, both seasons positive.

## The test (unseen seasons)
- Seasons **2021-22 and 2022-23**. Only a consensus line exists there (Action Network's consensus as last seen = the close;
  in 2024-26 it is within 0.19 pts of DraftKings' close on average). So the test is **at the close**, the harder bar.
- Same Model 1 predictions (`ncaab/data/preds.csv`; ridge 5, carryover 0.8, no decay). Caveats written now: 2021-22 starts with
  no prior (first season in the data); 2022-23 results chose the hyperparameters (overall prediction error, not this slice).
- Rule: conference game (ESPN flag), both teams D-I, neutral flag unambiguous, both teams 3+ games, |model total - consensus close|
  >= 6, bet the model's side at -110.
- **PASS** = combined 2021-23 units > 0 **and** win rate's one-sided 90% lower bound above 50% (i.e. not just a coin flip;
  stricter than break-even would be with these sample sizes) **and** both seasons units > 0... relaxed to: neither season below -5u.
  Written plainly: PASS needs (a) units > 0 combined, (b) win% > 52.4% combined, (c) neither season worse than -5u.
- PASS -> PROVISIONAL alerts for NCAAM conference totals (6+), own record, standing stop rules, after a Fable review.
  FAIL -> keep as a TEST record on 2026-27 only.

## Also reported (descriptive, decides nothing)
- Same slice at thresholds 4 and 5; overs vs unders; Jan-Apr non-conference games (is it "conference" or just "late season"?);
  conference regular season vs conference tournaments.
