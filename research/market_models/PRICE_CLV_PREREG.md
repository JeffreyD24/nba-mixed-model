# Pre-registration: CLV in price terms (closing out "juice skew", plan idea 2, Nov 5 2026)

Written and pushed before any result below is computed.

## Why
Point CLV ignores price. A total that closes 224.5 at -125/+105 is not the same as 224.5 at -110/-110. Step 3 (movement
model) already answered half of plan idea 2: Pinnacle's price lean predicts DraftKings' move (ridge weight +0.16) and
DraftKings' own lean adds about nothing. This closes the other half: grade CLV with the price included, so the record and the
promotion rule (GOALS.md) don't reward or punish a model for point moves that the price undoes.

## Method (NBA full-game totals and spreads, DraftKings and Pinnacle, The Odds API snapshots 2021-22 to 2025-26)
1. **No-vig probability** of each side at a snapshot: multiplicative de-vig of the two prices.
2. **Points-per-probability slope k** per market (totals, spreads): fitted on **2021-22 to 2023-24 only**. At DK's closing
   line, regress the over (home-cover) result, pushes dropped, on the no-vig probability and on the distance between line and
   result scale, i.e. estimate how many points one unit of no-vig probability is worth: k = 1 / (win-rate change per point of
   line), measured from the DK-close CLV table method (step 3 check) on those seasons.
3. **Effective line** = point + k x (p_over_novig - 0.5) for totals (spread analog: home side).
4. **Price CLV** of a bet = expected value at the bet's actual price, using the no-vig closing probability moved to the bet's
   line: p_bet = p_close_novig(side) + (bet line - close line, signed in the bet's favour) / k; EV = p_bet x decimal_odds - 1.
   Reported against both DK's no-vig close and Pinnacle's no-vig close. Break-even is 0%.

## Tests and decision rules (fixed now)
- **T1 (does the price carry information?)** On 2024-25 and 2025-26 separately (never used to fit k): Brier score of the
  over (home cover) result at DK's closing **point** line, predicted (a) by 0.5 + nothing (point-only), (b) by DK's no-vig
  closing probability. **Pass** if (b) beats (a) in both seasons. Same for Pinnacle's close.
- **T2 (does DK's own skew at first-seen predict the move?)** Descriptive confirmation of step 3: slope of (DK effective close
  minus DK first-seen point) on DK's first-seen skew in effective points, 2025-26. Expected near 0 for DK, positive for
  Pinnacle's skew at the same snapshot.
- **T3 (re-grade).** Re-grade in price CLV, both closes: (i) step 3 pre-registered movement bets 2025-26 (573), (ii) step 2
  residual bets 2025-26 if reconstructable, (iii) live 2026-27 NBA totals and spreads picks in state/picks_log*.csv, priced
  from research/live_odds at the lock time where a DK snapshot exists within 10 minutes.
- **Decision.** If T1 passes, price CLV becomes the reported CLV for NBA totals and spreads alongside point CLV (both columns
  kept). No live bet rule or threshold changes from this test. Any verdict that flips sign between point CLV and price CLV is
  listed explicitly.

## Leakage
Prices are taken from the same snapshot as the line; a later price is never paired with an earlier line. k is fitted on
2021-24 only. Pinnacle is used only as a closing reference, never as a bet-time input.
