# r/algobetting thread 1kl9thu (original post deleted; comments pasted by the user Nov 3, 2026)
Original post and the GitHub link are gone, so the repo it pointed to is unknown. Three comments survive. Unverified opinions; names left out.

1. **Backtest advice (the useful one).** Make five train/test splits (20% test) and require every one to be profitable; then bootstrap each test split (about 200 resamples with replacement) and plot 200 profit curves, not one. Even a truly profitable model will show many losing curves at that sample size, so a single profit line is just one draw.
2. A commenter uses the Odds API for odds and scrapes other sites for analytics data (offers to DM).
3. A commenter says they have scrapers and some historical pre-game and live odds (offers to DM).

## My reading
- The bootstrap point is sound for judging noise: with a few hundred bets, a profit curve is mostly luck. The average over resamples just equals the original result, so the value is the spread: report a confidence interval on ROI and CLV, and the share of resamples that lose.
- Random 20/80 splits are wrong for our models (they would leak the future). Use our walk-forward seasons as the "folds", and resample bets inside each season.
- Nothing here to chase from the DM offers (private, unverifiable).

## Action
Added to the checklist (section A): bootstrap interval for ROI and CLV on every tracked rule. Small job, Sonnet is fine.
