# NCAAM Model 2 tournament: pre-registration (Nov 5, 2026)

Pushed before any entrant is graded. Goal (Jeffrey): build several models, test them against each other, against the books' own
numbers (opening and closing lines), and against results, on CLV, accuracy and units. The group ideas (conference games, two power
conferences, early-season non-conference games) were spotted on 2023-26, so the deciding test uses seasons none of them has seen.

## Data (one file, `ncaab/data/all_games.csv`, built by `ncaab/build_all_games.py`)
ESPN scoreboard for every D-I game 2007-08..2025-26 (team ids, conference, neutral site, conference game) joined by date + score to the
lines: SportsbookReview open/close 2007-21; Action Network Open, consensus/DraftKings close and the books' own openers (ESPN feed,
DraftKings else ESPN BET, flipped-sign quotes dropped) 2021-26. Team keys = ESPN team ids, consistent across every season.

## Seasons (end-year labels)
2008 warm-up · **2009-2011 tuning** (knobs chosen on prediction error vs results only, no lines) · **2012-2015 fit** (thresholds; stack weights
start here) · **2016-2021 TEST (decides)** · 2022-2026 report (partly seen; DraftKings check only).

## Entrants (walk-forward, refit every game date, base ridge 5 / carryover 0.8 as in Model 1)
- **M1** Model 1. **M2** moving scoring level (half-life 14 days, chosen Nov 5). **M4** log points (ridge 5).
- **M8 conference hierarchy (new):** team effects shrunk toward their conference's effect (offense and defense per conference-season)
  instead of toward zero, the herd / contemporary-group idea from animal breeding. Knobs: team ridge {5, 10, 20} x conference ridge {1, 3, 10}.
- **M10** M8 + moving level + log points.
- **S-stack (new, the group idea):** fair line = opener + b0 x (model - opener) + b1 x (model - opener) x conference game + b2 x (model - opener)
  x both power conference + b3 x (model - opener) x Nov-Dec non-conference, fitted by least squares on all earlier seasons only
  (expanding window from 2012), on the best rating model by tuning-season error. Shrinks or trusts the model differently by group.
- **Benchmarks (the books' models):** the opening line and the closing line used as predictions.

## Measures (per entrant x market, test seasons)
Accuracy (RMSE vs results, next to the opener's and the close's) · beat-the-close slope (result - close on model - close, with t) ·
bets at the threshold vs the opener: count, win %, units at the opener, **CLV (opener to close, primary)**, units at the close, edge capture.
Thresholds per entrant chosen on 2012-15: smallest of {2,3,4,5,6} (stack {0.5,1,1.5,2,3}) whose CLV >= break-even
(0.0238 x sd(result - close) x sqrt(2 pi), from 2012-15).

## Winner and pass
Winner per market = highest test CLV; within 0.10 -> more units at the close. It goes PROVISIONAL only if, in 2016-21: CLV >= break-even,
CLV 90% low end > 0, units at the opener > 0, ROI at the close > -2%; **and** in 2024-26 at DraftKings' own opener (flip-filtered): units > 0
and CLV >= break-even. Then a Fable review. Otherwise TEST record. Every entrant's numbers are reported either way.
