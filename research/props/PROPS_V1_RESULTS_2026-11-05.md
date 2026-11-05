# NBA player props v1 / v1b — results (Nov 5, 2026)

Pre-registration `research/props/PROPS_V1_PREREG_2026-11-05.md` (commit cc4c5c8) + amendment 1 (v1b, commit 361cb3c) + amendment 2
(within-season split, commit d870629), all pushed before any prop result was computed. Script `analysis/props_v1.py`; outputs
`analysis/props_v1_output.txt`, `analysis/props_v1b_output.txt`; bets `analysis/props_v1*_bets.csv.gz`.
Lines: 2025-26, 6 books, 11 AM ET and 10 min before tip (The Odds API). ~22k player-market lines per half. Fit Oct 21–Jan 15, test Jan 16–Apr 12.

## Main result (rule: EV ≥ 5% at the better of DraftKings/FanDuel at 11 AM)
| | Half | Bets | Win % | Units | ROI [90%] | Closing-line EV [90%] |
|---|---|---|---|---|---|---|
| v1 | fit | 781 | 53.1% | +45.9 | +5.9% [−2.0, +13.5] | −0.9% [−1.7, −0.2] |
| v1 | **test** | 1,121 | 54.1% | **+79.2** | **+7.1% [+1.5, +12.9]** | **−2.3% [−3.4, −1.3]** |
| v1b | fit | 926 | 53.6% | +58.0 | +6.3% [−0.8, +13.1] | −1.1% [−1.9, −0.3] |
| v1b | **test** | 1,353 | 55.0% | **+116.0** | **+8.6% [+3.4, +13.9]** | **−2.2% [−3.0, −1.2]** |

**Verdict by the written rule: both fail** (closing-line EV is negative, CI below 0), even though units are positive in both halves.

## Why the money and the closing line disagree
- **Every book's close leans to overs.** Across all ~250k close lines, the no-vig over probability averages 49.0–49.6% while overs
  actually hit 47.5–48.8% (threes worst: 48.2% priced vs 46.1% hit). So the close undercounts unders by ~1.2 points of probability,
  which by itself makes closing-line EV on unders look ~2% worse than it is. Our bets are 85–90% unders. Adjusting for that bias,
  closing-line EV is roughly 0, not positive.
- Betting every under blindly still loses (DK −3.7%, FD −4.3%, Pinnacle −4.4% at 11 AM): the bias is smaller than the vig.
- **Does the model know anything the close doesn't?** Logistic check on the outcome with the close and (model − close):
  test-half coefficient on the model +0.02 (se 0.03): **no information beyond the close.** (Fit half +0.10, se 0.04.)
- **Almost all profit was at FanDuel** (v1b: FD 960 bets +115.4u, +12.0%; DK 393 bets +0.6u). Picking the better of two books'
  prices is real value, but it also means the record depends on FanDuel's 11 AM prop prices specifically.
- Rows split by "line moved toward us" use the close, so they're lookahead and not a usable filter.

## Decision (Claude, under the standing permission; flagged)
- **No real-money prop bets.** Same standard as the derivatives test: units without closing-line support isn't proof.
- **Props v1b goes on a free shadow (paper) record for 2026-27**, graded daily, at whatever books we can get live prices for.
  If it keeps winning at FanDuel with closing-line EV near 0 or better after ~500 bets, it gets a PROVISIONAL real-money trial
  (after a Fable check).
- The **under bias at the close** goes in TRENDS as its own finding: a starting point for an unders-only prop model.

## Takeaways
1. **Props are softer than sides, but not soft enough for a box-score model alone.** The model's raw probabilities were worse than the
   11 AM market (log loss 0.713 vs 0.688); only a 21% model / 79% market blend helped, and by the close it added nothing.
2. **The edge that showed up is structural, not model-driven:** books shade overs (public likes overs), FanDuel's morning prices lag,
   and shopping two books catches both. That's worth pursuing directly: an "under at the better book when the market leans over"
   rule is the next pre-registration.
3. **What the model is missing is the same thing the market prices fast: who's playing.** Minutes is the biggest driver of every prop,
   and our minutes projection ignores same-day injuries/rest. That's the v2 upgrade (injury report + rotation data we already collect).
4. Process: the 2024-25 line download was lost to a workflow bug (fixed). That's why this used a within-season split; treat it as weaker
   evidence than a season-on-season test.
