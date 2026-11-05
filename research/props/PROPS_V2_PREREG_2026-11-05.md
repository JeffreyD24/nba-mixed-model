# NBA player props v2 — injury/rest-aware minutes — pre-registration (written Nov 5, 2026, before any v2 result)

## What changes from v1b (`research/props/PROPS_V1_PREREG_2026-11-05.md`, frozen in data/props_v1b_params.json)
Uses the official NBA injury reports (`research/injury_history/`, every published snapshot 2021-26), taking the **latest report
published before the bet time**:
1. **Own status:** Out / Doubtful → no bet. **Questionable → no bet** (fixed now; too uncertain). Probable / Available / not listed → keep.
2. **Teammates out:** M_out = sum of the projected minutes of teammates listed Out or Doubtful. Their minutes go to the remaining
   players in proportion to each one's projected minutes (cap 40 min per player).
3. **Usage bump:** each remaining player's per-minute rate × (1 + α_stat × M_out / 240), α_stat fit on 2023-24 BOX SCORES ONLY
   (regression of actual per-minute stat ÷ projected rate on M_out / 240, players with 15+ minutes), no prop lines used.
Everything else (rates, opponent, pace, mean-dependent spread, negative binomial) is v1b.

## Data, bet times and seasons
- **Fit (blend weight w only): 2023-24**, BettingPros closes (bet at the best of DK/FD close; report = latest before tip − 30 min).
- **Test A (primary): 2024-25**, same setup. **Test B: 2025-26**, The Odds API 11 AM lines (report = latest before 11 AM ET),
  graded with closing-line EV as in v1.
- 2022-23 descriptive (fewer books).

## Measures and pass (primary = Test A)
1. **Primary:** the model knows something the close doesn't — logistic regression of the over outcome on logit(close no-vig) and
   (logit(p_model) − logit(close)), with an intercept (the close's over-lean): coefficient on the model term > 0 with a 90% CI above 0.
2. Second: bets (EV ≥ 5% vs the best of DK/FD close price) make units > 0 in Test A.
3. Reported alongside: Test B closing-line EV and units, log loss vs the market, v2 vs v1b side by side on the same rows.
Pass = 1 and 2. A pass goes live only as PROVISIONAL after a Fable check; until then it joins the paper record next to v1b.

## Implementation note (Nov 5, 2026, before any prop result)
The α regression weighted by minutes gave α = +314 for threes (players who almost never shoot threes make actual ÷ projected explode).
It is now weighted by the expected count (minutes × projected rate): α = Σ x·(actual − expected) / Σ expected·x². Box scores only, as before.
