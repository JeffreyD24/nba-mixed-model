# Props v1b at the OPENING line, past seasons — pre-registration (written Nov 5, 2026, before any opener result)

## Why
v1b's profit at 11 AM (2025-26) was model-driven, but at the close it nets ~0. If the model is ahead of the *early* market, betting the
opener should show it on past seasons (RULE 2: not the current season). BettingPros keeps each prop's opening line + price + book +
time (both sides, same book and line), Dec 2021 on. Coverage check only so far: openers median ~10 h before tip.

## Model
v1b exactly as frozen (`data/props_v1b_params.json`: rates, minutes, opponent, pace, mean-dependent negative binomial), features from
games before the game date. **Timing guard:** a bet counts only if the player's previous game was on an earlier ET calendar day than the
opener's posting time (so no opener is graded with a result that happened after it was posted), and the opener was posted 1+ hour
before the scheduled tip.

## Bet rule
- Market at the opener = the opener's own two prices, de-vigged.  p = w·p_model + (1 − w)·p_open.
- **w fit on 2022-23 openers only** (log loss). Bet the side with EV ≥ 5% at the **opening price**, only when the opening book is
  DraftKings or FanDuel (bettable here). One bet per player-stat-game. Players who don't play are void.
- **Test: 2023-24 and 2024-25** (unseen at the opener). 2025-26 and 2021-22 descriptive. Thresholds 3/8/12% descriptive only.

## Pass (this is a negative-CLV idea, so the extra checks in research/PROVISIONAL_BETS.md apply; all needed)
1. **Unseen seasons:** units > 0 in BOTH test seasons, and pooled test ROI with a 90% bootstrap CI (by date) above 0.
2. **CLV, adjusted for the close's over-lean:** closing-line EV of the bets = same book's close no-vig (moved to our line with a normal
   shift, as in v1) × our opening price − 1. Lean adjustment: the close's average over-lean (no-vig over minus actual over rate)
   measured on the OTHER seasons (leave-one-season-out), added back to the under side / subtracted from the over side.
   Pass = lean-adjusted closing-line EV ≥ 0 pooled over the test seasons.
3. **Beats the simple versions on the same opener rows:** (a) the same rule with w = 0 (no model), (b) every under at the opener at
   DK/FD. The model rule's test-season units must exceed both.
4. Fable review before anything goes live; then Jeffrey decides on a PROVISIONAL record.
Also reported: raw closing-line EV, by stat / side / book, line movement opener → close in our direction (true CLV in points).
