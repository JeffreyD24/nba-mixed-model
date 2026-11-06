# Independent review (Fable) of the Polymarket follow-test grader, Nov 6, 2026

Verdict: **OK with caveats.** No look-ahead across periods, no side/price/won bugs. Independent recompute of all 238 NFL
primary-list bets from raw fills: same sides and outcomes, entry differences <= 0.004, ROI -0.0111 vs grader -0.0109.

Small deviations (none change the sign): own price weighted by shares not money (poly_follow_grade.py:57); merged bet entry is the
unweighted mean of wallets (pre-reg silent); pushes (0.5|0.5) dropped instead of graded 0 (wallet_rankings.py:46); bootstrap is
re-drawn for the verdict (printed -0.0173 vs verdict -0.0176); period split uses the UTC date of game start.

Caveats that matter for the read:
- Within-market look-ahead in the entry: the signal is the wallet's NET pre-game position (known only at game start) but the entry is
  its average fill price, often hours earlier; 36% of primary wallet x market combos traded both sides. A follower can't get the
  early price AND know the final side. roi_close is the leak-free number: +0.0278 pooled, NHL +0.0323, NFL +0.0003.
- The primary list is mostly market makers: CLV vs the last trade is positive for resting-order wallets (spread capture) and t >= 2
  selects volume. Entries' CLV ~ 0 (0.0004): the follower pays about the close, so any ROI comes from the close itself.
- 3% exact duplicate fill rows in NFL (14% in Feb), look like real repeated matches; affect risk thresholds and counts, not sides.
- Profit concentrates in longshots: ROI +0.114 on 352 bets with entry <= 0.30, -0.035 at 0.45-0.55.
- Baseline pool includes other primary wallets (conservative).
Result stands as LEAD; report roi_close, the maker-selection point and the entry caveat.
