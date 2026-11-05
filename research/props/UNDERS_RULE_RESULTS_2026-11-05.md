# NBA prop unders at the best book — results (Nov 5, 2026)

Pre-registration `research/props/UNDERS_RULE_PREREG_2026-11-05.md` (+ timestamp amendment, both pushed before the primary seasons were
run). Script `analysis/props_unders.py`, output `analysis/props_unders_output.txt`, bets `analysis/props_unders_bets.csv.gz`.
Data: BettingPros closes, Dec 2021 – Nov 2026, 2.6M book-lines; 311k under bets, 97.8% matched to box scores.

## Result: does not pass. Blind unders lose even at the best of four books.
| Season | Bets | Win % | Units | ROI [90%] | Close over-lean (priced vs hit) |
|---|---|---|---|---|---|
| 2021-22 | 38,261 | 52.5% | −758 | −2.0% [−2.8, −1.2] | 49.6% vs 48.0% |
| **2022-23** | 54,852 | 53.0% | −687 | −1.3% [−2.0, −0.5] | 49.5% vs 48.0% |
| **2023-24** | 62,823 | 52.7% | −1,120 | −1.8% [−2.5, −1.1] | 49.6% vs 48.4% |
| **2024-25** | 68,764 | 53.1% | −1,314 | −1.9% [−2.6, −1.3] | 49.5% vs 48.6% |
| 2025-26 | 69,308 | 53.5% | −657 | −1.0% [−1.6, −0.3] | 49.4% vs 48.1% |
**Primary pooled (bold seasons): 186,439 bets, −1.67% [−2.08, −1.25], 0 of 3 seasons positive → fail.**

## What it shows
- **The over-lean is real and steady:** every season the consensus close prices overs ~1–1.6 points of probability too high.
- **Shopping helps a lot, but not enough:** one book's unders lose 3.0–5.0%; the best of four loses 1.7%. The lean is smaller than the vig.
- **Where blind unders are worst / best:** assists (−4.8%) and tiny lines 0.5–2 (−4.9%) are worst; rebounds (+0.5%) and lines 20+
  (+1.4%) are near break-even, neither significant.
- DraftKings was the best single book to take the under at (−0.9% when chosen), FanDuel −1.9%.

## Takeaways
1. A rule built on the lean alone isn't a bet. The lean needs a second filter that finds the unders the market misprices most.
2. That is what the props models do: their *selected* unders were profitable (see the v2 results doc). The model, not the lean, is the
   part worth testing further.
3. Closing-line value for props must be adjusted for this lean, or under bets will always look ~2% worse than they are.
