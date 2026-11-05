# NBA player props v2 (injury-aware minutes) — results + review (Nov 5, 2026)

Pre-registration `research/props/PROPS_V2_PREREG_2026-11-05.md` (+ α implementation note, before results). Script `analysis/props_v2.py`,
output `analysis/props_v2_output.txt`, bets `analysis/props_v2_close_bets.csv.gz` (v1b on the same rows: `props_v1b_close_bets.csv.gz`).
Independent review: `research/props/reviews/FABLE_REVIEW_PROPS_V2_2026-11-05.md`.
Data: BettingPros DK/FD closes 2022-26 (~52k player-stat-games per season with both books at the same line), official injury reports.

## Pre-registered result (Test A = 2024-25)
| | Model-beyond-close coef [90%] | Bets | Units | ROI [90%] |
|---|---|---|---|---|
| v2 fit 2023-24 | +0.101 [+0.071, +0.132] | 646 | +8.1 | +1.3% |
| **v2 Test A 2024-25** | **+0.103 [+0.073, +0.133]** | 1,299 | **+8.7** | +0.7% [−3.9, +5.4] |
| v2 2025-26 (descr.) | +0.093 | 1,645 | +80.2 | +4.9% |
| v2 2022-23 (descr.) | +0.037 | 505 | −35.0 | −6.9% |
By the letter of the plan, **v2 passed** (coefficient CI above 0, units above 0).

## Why it is NOT going live anyway (Fable review, confirmed)
1. **The bets weren't the model's.** All Test A bets were FanDuel prices judged against DraftKings' no-vig price; with the model's weight
   only 7%, the bets are mostly *FanDuel vs DraftKings disagreements at the close*. With no model at all the same rule makes +61u;
   the 425 bets that needed the model to qualify lost −50u (−11.7%).
2. **Many of those disagreements are stale lines.** BettingPros keeps each book's *last* update; 118 bets used FanDuel prices stamped
   after tip, and bets where one book's line was 1h+ older lost 10–15%. Not placeable.
3. **v2's minutes double-count injuries:** recent averages already reflect long absences, and v2 added those minutes again
   (team total 272 projected minutes vs 239 actual). That pushed it to overs (77% of bets), which lost.
4. The information test itself held up (date-clustered SEs, stat × line controls, a no-information null at −0.17): **the model does
   carry a little information the close doesn't** (coefficient ≈ +0.1 every season, v1b too). It's just too small to beat the vig at
   the close.

## Decision (Claude, flagged): no live bets from v2. Fix list for a v2.1 pre-registration:
rescale projected minutes to 240 per team; only redistribute absences newer than the player's recent games; judge each bet against
its own book; require both books updated within 15 min before bet time and before tip; run Test B (11 AM, The Odds API 2025-26).

## Props v1b, revisited (the +116u question)
- At the **11 AM** snapshot (The Odds API 2025-26, both books captured at the same moment) the profit **is the model's**: with no model
  only 48–62 bets qualify (≈0u); the bets that needed the model made **+54.8u (fit half) and +110.3u (test half)**.
  In the test half that was almost all FanDuel (+109.6u; DraftKings +0.6u).
- At the **close** (BettingPros, 4 seasons) the same model's own bets net ≈0: −147u (2022-23), +47u, +17u, +77u.
- Reading: the model knows things the **morning** market hasn't priced yet (mostly unders), and by tip the market has caught up.
  That is the kind of edge that only works if you bet early — which the live FanDuel paper record (11 AM picks) tests directly.
- Against the extra checks for negative-CLV ideas (research/PROVISIONAL_BETS.md): unseen-season units at the real bet time can't be
  checked (no 11 AM lines before 2025-26), and at the close 2022-23 is clearly negative. **So v1b doesn't qualify yet; recommendation:
  keep the 11 AM FanDuel paper record running (≈10–15 picks/day, ~500 by mid-December) and decide then.**

## Takeaways
1. Cross-book "edges" at the close are mostly stale prices. Any book-vs-book rule needs synchronized snapshots, not last-update data.
2. Our player model carries real but small information (coef ≈ +0.1) — worth more in the morning than at the close.
3. Bet timing is the lever for props: the morning is where the model's information hasn't been priced in yet.
