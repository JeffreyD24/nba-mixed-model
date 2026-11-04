# Pre-registration: how far can a line move against the model before we pass? (Nov 4, 2026)

Written and pushed **before any result is computed.** Jeffrey's question: the live rule passes when the line has moved 0.5+ pts
against the model since DraftKings' open. Is 0.5 too strict? Is an early move (first ~30-60 min) different from a later one? Do
lines that move against us swing back?

## Data
- **Main (in-sample, descriptive):** DraftKings 2023-24 .. 2025-26, live totals number and live spread number exactly as in
  `analysis/rule_audit_injury_timing.py` / `analysis/rule_audit_spreads.py` (morning-lock lag 1, both teams 10+ games; spreads only in
  the live windows). Line path from `data/odds_history/nba_snapshots.csv.gz` (DraftKings rows). These seasons built v4, so this set
  can describe but not confirm.
- **Out of sample (confirm):** SBR openers/closers 2013-14 .. 2021-22 with Model 1 (no injury features) from
  `analysis/old_seasons_sbr_bets.csv`. Open and close only, so it can test move SIZE, not timing. Reported with and without the two
  COVID seasons (2019-20, 2020-21).
- Snapshots are mostly hourly (some 5-15 min), so "early" = the first snapshot at least 30 min and at most 90 min after the open.
  A true 30-minute window can only be measured on the 2026-27 live 5-minute checks (shadow record, below).

## Bet set
Every game with edge 3+ at the opener. Edge at the opener uses the previous game's injury report (what is known when the line posts);
lines checked at night use the 8 PM report. A "move against" = the line moved away from the model's side by 0.5+ since the open.

## Tests (all graded at -110; CLV = closing line minus bet line in the bet's favor, in points)
- **T1 size:** bet at the moved line, grouped by move size since open: 0.5, 1.0, 1.5, 2.0-2.5, 3+. Checked at the early line, 9 PM,
  9 AM game day, and the close. Same buckets for "toward" and "unmoved" as reference.
- **T2 timing:** among lines that moved 0.5+ against, early movers (by the early line) vs. later movers (unmoved early, against by
  9 AM). Grade both at the 9 AM line and at the close.
- **T3 swing-back:** among early against-moves, share whose close came back to the opener or past it, share that kept moving against,
  and the CLV of betting the moved line early vs. waiting.
- **T4 news:** split against-moves by whether the 8 PM report moved the model 1+ pt in the same direction as the line ("news")
  vs. not ("no news").

## Decision rule (fixed now)
The PASS threshold is loosened from 0.5 to X (X = 1.0, 1.5 or 2.0, smallest that qualifies) for a market only if the bucket
"0.5 to under X against", bet at the line when seen, meets ALL of:
1. average CLV >= 0 (primary),
2. units > 0 overall and in at least 2 of 3 DK seasons (second check),
3. win rate >= 52.4% reported alongside, and
4. the same size bucket at the SBR close is > 0 units out of sample (spreads and totals separately).
If 1-3 pass but 4 fails: no change; the bucket becomes a PROVISIONAL watch item tracked in the shadow record.
If 1-4 pass: the looser rule goes in as PROVISIONAL (standing rule for unproven ideas), reviewed monthly, stopped if it loses.
T2-T4 are descriptive: they can add a condition (e.g. "no news" only, or "early only") but cannot by themselves loosen the rule.
Nothing goes live without Fable's review.

## Shadow record (starts tonight, live)
Every 3+ edge game the rules PASS because the line moved against is logged with: opener, line when passed, move size, minutes since
open, whether an injury report changed the model, and graded at both the passed line and the close. Reviewed with the monthly
PROVISIONAL review; the 5-minute data answers the 30-minute question.
