# Props v1b at the opener — clean re-test (pre-registration, Nov 5, 2026, before running it)

Jeffrey chose paper only for now (Nov 5) and asked for the extra past-season checks first. The Fable review found 2023-24 was not a
clean test season, because v1b's spread settings (`var_ab`) were fit on 2023-24 box scores.

## The one change
- `var_ab` (variance = a·μ + b·μ² per stat) is refit on **2022-23 box scores only**, the same season the blend weight w is fit on.
  This makes **both 2023-24 and 2024-25 clean test seasons**. Everything else in `PROPS_V1B_OPENER_PREREG_2026-11-05.md` is unchanged:
  features, timing guard, DK/FD openers, EV ≥ 5% at the opening price, and the three pass checks.
- Data fix from the review: lines below 0.5 are dropped (6 bets were on a 0.0 line, which can't win an under).

## Reported
- **Primary:** the original rule (openers 1h+ before tip). The pass checks apply to this rule.
- **Secondary, descriptive only:** FanDuel openers posted 4h+ before tip. This slice was suggested after seeing results, so it can't
  pass anything here.
- The lean-adjusted close-EV gets a 90% bootstrap CI.
- April vs Oct–Mar, by season (the April [LEAD]).
