# Step 4 pre-registration: blend for NBA totals (our model + market + expected move)

Written Nov 5, 2026, **before** any blend was fit or any result looked at.

## Question
What is the best estimate of the final total, and does betting the gap between that estimate and DraftKings beat
the live totals rule (v4 alone)?

## Pieces (all known at the decision moment)
- **v4**: the live totals model's prediction (`analysis/threshold_sweep_2026-11-04/nba_v4_preds.csv`: walk-forward,
  one-day results lag, opener-time injury report; 2023-24 to 2025-26). Caveat: v4's add-ons (luck, form, altitude) were
  chosen on these seasons, so v4 is partly in-sample. That favors v4 in both the blend and the baseline.
- **DK now**: DraftKings' total at the decision snapshot (The Odds API history, Action Network books only, as live).
- **Expected move**: the step-3 movement model "v1-an" prediction at that snapshot, refit season by season on earlier
  seasons only (2024-25 predicted by a model fit on 2022-23 to 2023-24; 2025-26 by one fit on 2022-23 to 2024-25).

## Decision moment
The **first DraftKings snapshot at or after 9:00 PM ET the night before** (the 8 PM injury report is out, so v4's
inputs were all known), or DK's first-seen line if it appears later. Games 0.5 h+ before tip. One decision per game.

## Blend
Fair = a + w_v4 * v4 + w_mkt * (DK now + expected move), least squares on the final total.
Weights fit on 2023-24 and 2024-25, scored **once** on 2025-26. The fitted weights are reported: w_v4 says how much our
model adds beyond the market's expected close.

## Bet rule tested on 2025-26 (fixed now)
Edge = Fair - DK now. Bet DK when |edge| >= **2.0** pts, Over if positive, at DK's line and price at the decision snapshot.
- Break-even CLV +1.07 pts (NBA full-game totals). Grade: CLV vs DK close first, units (1 unit, actual price) second, win % alongside.
- **Baseline on the same games and snapshot:** v4 alone with the live threshold (|v4 - DK now| >= 2.5).
- **Pass:** blend CLV >= +1.07, units > 0, **and** blend CLV per bet above the baseline's. Pass -> PROVISIONAL alerts
  (Jeffrey Nov 5: provisional ideas go live with money, labeled, own record), Fable check first. Fail -> noted, not bet.
- Exploratory only: thresholds 1.5 and 3.0; the decision at DK's first-seen line instead; the 2024-25 season; blend
  without the expected move (v4 + DK now only).
