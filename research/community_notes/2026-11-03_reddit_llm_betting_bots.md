# r/algobetting thread 1ktxben: "Can large language models discover profitable sports betting strategies?"
Pasted by the user Nov 3, 2026. Unverified. Names left out. The post reads partly as promotion for a betting-tracking app (EQULS); the author tracks bot picks there and says the record is public. I did not check it.

## What was claimed
- A student ran 99 LLM "bettor persona" bots (25 in the pilot, 13 betting) fed odds, stats, public splits and weather through a ~10-step prompt flow.
- Early numbers: 7 of 13 active bots profitable, ROI like +55% on 9 bets and +36% on 3 bets. The author admits this is meaningless at that size, expects all bots to end unprofitable, and later said two bots were "up over 20u".
- Backtesting is skipped because it would cost about $1.5k and 400 hours for 1,000 bets per bot.
- Author's own finding: social-media sentiment was not a useful signal for their predictive models (probably already priced in). Says 4 TB of odds/stats data collected in a month; the data pipeline matters more than the LLM.

## Useful points from commenters
1. 7 of 13 winning bots after 3-11 bets each is what pure luck looks like. Same trap as our own early bet logs: judge only after hundreds of bets (the author planned t-tests with a Benjamini-Hochberg correction for testing many bots at once, which is the right idea).
2. **Market as a feature (our shrink test, formalized).** One commenter's recipe: split history 60/20/20; tune prompts/features on the first 60%; fit a regularized logistic regression on the next 20% using the model probabilities PLUS the market's probability as inputs; test profit on the last 20%. This is the same idea as our market-shrink weight (checklist B). For us: do it per sport with walk-forward seasons, not fixed random blocks.
3. A betting market is a probability-estimation game: you need NEW information or better interpretation, not already-priced information plus noise.
4. Where an LLM could plausibly help: reading news for things the line has not absorbed (injuries, stadium wind effects), used as a feature in a normal model, not as the decision maker. Commenters who "improved results with LLMs" said they already had a working model first.
5. A linked library scrapes Reddit/Twitter sentiment. Not adopted: the author found sentiment not useful, and scraping both sites may break their terms.

## Takeaways for us
- Nothing to build now. Confirms the order of work: measure with CLV and intervals, shrink toward the market, only then add exotic signals.
- Park: LLM-read injury/news as an input for a late-scratch check, tested on logged cases only.
