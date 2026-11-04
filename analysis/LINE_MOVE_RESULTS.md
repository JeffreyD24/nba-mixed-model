# Line moved against the model: is the 0.5-pt PASS too strict? Results (Nov 4, 2026)

Pre-registration: `analysis/LINE_MOVE_PREREG.md` (commit f60b0e5, pushed before any result). Code: `analysis/line_move_threshold.py`.
Full output: `analysis/line_move_threshold_output.txt`; every bet: `analysis/line_move_threshold_bets.csv`. Reviewed by Fable (fixes applied:
pooled first-seen decision bucket, early edges on the previous-game report, unmoved bucket overlap, shadow-record swing-back definition).

## Bottom line
**No change to the PASS rule.** Lines that move against the model are information, not a gift. The live-relevant loosening (allow a
1.0-pt move) looked good on DraftKings 2023-26 for totals but failed out of sample, so by the pre-registered rule it becomes a watch item
in the new shadow record, not a bet.

**Important fact found in review:** DraftKings has posted only half-point totals and spreads since Oct 2025 (100% of 2025-26 snapshots and
of this season's 5-minute checks). Live lines move in whole points, so "0.5+ against" really means "1.0+ against" now, and the only real
loosening on the table is "allow a 1-pt move".

## What the tests showed
| Test | Totals | Spreads |
|---|---|---|
| Decision bucket, 0.5 to under 1.5 against, bet when first seen (DK 2023-26) | 377 bets 55.4% **+22.0u**, CLV +0.49, seasons -4.5/+14.4/+12.1 (criteria 1-3 pass) | 85 bets 48.2% -6.7u (fails) |
| Live-relevant: exactly 1.0 against when first seen (DK 2023-26, added after review) | 239 bets 56.9% +20.6u, CLV +0.53, seasons -7.5/+15.0/+13.2 | 38 bets 47.4% -3.6u |
| Out of sample, SBR 2013-22, bucket 0.5 to under 1.5 at the close | +7.6u all seasons, **-1.9u without the COVID seasons** | +1.9u / +16.5u |
| Out of sample, exactly 1.0 against at the close | **-6.4u / -10.6u** without COVID | -0.9u / +13.5u |

Criterion 4 (out of sample > 0) fails for totals on the reading that matches Jeffrey's choice to leave out the COVID seasons, and fails clearly
for the live-relevant 1-pt step. Spreads fail in sample. Per the pre-registration: **no change; totals "1-pt move against" is a PROVISIONAL
watch item (tracked, not bet).**

**Size matters a lot (out of sample, 9 seasons, ~4,300 totals bets graded at the opener):** the bigger the eventual move against, the worse
the bet: 0.5 pts 53.6%, 1.0 49.3%, 1.5 46.4%, 2-2.5 42.2%, 3+ 37.4%. Moves toward the model: 58.0%. Spreads show the same slope
(50.6% down to 32-38%). Even bet at the better closing number, moves of 1+ pt against lose.

**Early moves are not "sharps we can ride with".** When the line moves away from the model, someone is betting the other side. Totals that moved
against within 90 min of the open won 48.8% at the opener (-11.5u); 90 min-6 h 48.4%. Moves that came 6 h+ after the open did fine for totals
(+33.7u at 9 AM; note that group mixes lines already against by 9 AM with ones that moved later) but lost for spreads (-8.8u). Early, sharp-hour
moves are the most informative, and they point against us.

**Swing-back happens but doesn't pay.** Of totals 0.5+ against 30-90 min after the open, 46% were back at the opener or better by the close
(vs. 33% of unmoved lines dropping below theirs), but betting the moved line early still went 46.7%, -11.5u on 105. The line coming back isn't
the same as the bet winning.

**News is the dividing line (descriptive).** Totals moved against at 9 AM: when the 8 PM report had also moved the model 1+ pt the same way,
44.6% (-12.4u, 83 bets); without news, 57.3% (+37.3u, 398). Spreads lost either way.

## What changed live
Nothing about betting. New: `shadow_passed.py` runs every morning and writes `state/shadow_passed.md` / `.csv`: every 3+ edge game passed for a
move against, graded at the passed line, the close and the opener, split by move size, minutes from open to the move (first 30 min / 30-90 /
90 min-6 h / 6 h+, from the 5-minute checks), and news. It is in the daily health check. Moves of 8+ pts on a total (6+ on a spread) are left
out as suspect openers.

## Personal note / takeaways
- Your instinct that early movers might be sharps is right about who moves early, but it cuts the other way: the sharps are on the other side
  of our bet. Treat an early move against as a second opinion that disagrees with the model.
- The best version of "don't miss good bets" is betting the opener faster, not betting after the move: every 3+ edge opener bet at the
  opener was +109.3u in 2023-26 (CLV +1.45 pts), far better than any bucket of moved-against lines.
- The closest call is totals with a 1-pt move against and no injury news. It's in the shadow record; at ~100 shadow rows (likely by
  mid-season) we re-run this test with 2026-27 added and decide.
- Carry-over to other markets: price moves against your view right after a release are the most informed ones; fading them rarely pays.
