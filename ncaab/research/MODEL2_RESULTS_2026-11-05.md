# NCAAM Model 2 tournament: results (Nov 5, 2026)

Pre-registration `ncaab/research/MODEL2_PREREG_2026-11-05.md`. Code `ncaab/build_all_games.py`, `ncaab/model2_tournament.py`, `ncaab/model2_grade.py`.
Outputs `ncaab/research/model2_output.txt`, `model2_tuning.txt`, `model2_totals_diagnostics.txt`. 113k ESPN games 2007-26 with SBR / Action Network / book lines.
Entrants: M1 Model 1 · M2 moving scoring level · M4 log points · M8 conference hierarchy (team effects shrunk toward their conference) ·
M10 M8+M2+M4 · STACK (fair line: opener + model edge x group terms: conference game, both power, Nov-Dec non-conference).

## Results
- **Spreads: nothing passes.** No entrant reached break-even CLV in the 2012-15 fit seasons (break-even 0.63).
- **STACK (Jeffrey's group inputs): fails both markets** in the fit seasons; the group terms did not make the model's edge reliable.
- **Totals: M2 passed the rule on paper; M8 also cleared the fit seasons.**
| Totals 6+ | 2016-21 test (SBR opener) | At the close 2016-21 | Beat-the-close slope | 2024-26 at a book's own opener |
|---|---|---|---|---|
| M2 moving level | 1,439 bets 57.9%, +149.0u, CLV +1.77 (b/e 1.02) | +42.2u (+2.9%) | +0.120 (t +3.6) | 1,047 bets +7.9u, CLV +1.25 (all books) |
| M8 conference hierarchy | 2,653 bets 56.7%, +214.9u, CLV +1.64 | +64.3u (+2.4%) | +0.137 (t +4.4) | 1,725 bets +35.4u, CLV +1.02 |
M8 bets overs 72-90% of the time (the books' close ran 0.5-1.2 pts under results most seasons); vs the close directly 2016-26 M8 is -13.4u.
M2 is balanced (overs 47-62%) and won both sides in the test.

## Fable review: BLOCK (not live). Findings, all verified with numbers
1. The "book's own opener" check was one-third ESPN BET (2024-25 has no DraftKings rows). **DraftKings rows only: 566 bets 52.0%, -3.6u,
   CLV +1.21, close -4.9%** -> fails the rule's DraftKings condition.
2. Some SBR openers are unbettable garbage (e.g. 120 open / 155 close). Excluding bets with |open - close| >= 6: 1,320 bets 56.6%, +105.6u, CLV +1.21.
3. No edge over the close in 2024-26 (slope t 0.9 vs 3.7 in 2016-21); 2016-21 units at the close are not significant (90% CI -13u to +99u).
4. With a one-day data lag, 2024-26 units flip to -10.4u.
5. The "fewer than 8 games this season -> OTHER" team rule used the full-season count (not knowable live): immaterial in the backtest
   (+147.6u with the pre-game rule), but fixed for live use (`--live-rule`: no conference id -> OTHER).
6. The 2021-23 "close" (Action Network consensus) was captured after tip-off: those seasons' beat-the-close numbers are not usable.

## Decision and what runs now
- M2 totals: **TEST record at DraftKings' own opener** for 2026-27 (`ncaab/m2_daily.py`, in the 9:17 AM NCAAM job, health-checked).
  Fable re-review at ~300 DraftKings bets. Promote only if DraftKings-only units > 0 and CLV >= 1.02.
- Lesson for every future test: report the DraftKings-only slice separately; drop openers more than 6 pts from the close in old archives.
- What the tournament says about the model: the moving scoring level is the one change that helps totals; the conference hierarchy improves
  accuracy slightly (margin MSE 116.4 vs 117.4 in tuning) but turns into an overs bias; groups as stack terms add nothing.
