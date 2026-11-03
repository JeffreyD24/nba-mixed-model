# r/algobetting thread 1jz11vr: "end of first regular season my model is live" (NBA player props)
Pasted by the user Nov 3, 2026 with a screenshot of the author's results dashboard (2024-25 season). Self-reported, unverified. Names left out.

## What was claimed
- NBA player props (points, assists, rebounds), 2 years of experience, first live season (Nov 2024 to Apr 2025).
- Only bets where the model's stated probability is above 70%, $10 flat per bet.
- Dashboard: 2,170 bets, 60.0% accuracy, +$1,065.50. By market: points 55.3% (506 bets, +$156.50), assists 60.4% (893, +$96.00), rebounds 62.7% (771, +$813.00).
- Dropping the filter to above 60% lowers accuracy about 3 points; above 50% "is not profitable".
- Model ignores injuries on purpose; after the pick, a simple rule removes it if the player's numbers change a lot when a teammate is out (3+ games of evidence).
- Advice to beginners: start with linear regression, keep features lean, learn bias/variance, then boosted trees, avoid neural nets, build a reusable test function.

## What the numbers say (my checks)
- ROI is 4.9% on money staked (1,065.50 / 21,700). That fits the 60% hit rate only if the average price was about -134, not -110. At -110, 60% over 2,170 bets would have made about $3,150. So the prices were juiced, or the dashboard counts something differently.
- 95% interval on the 60.0% hit rate is about 57.9 to 62.1%. That clears -110 break-even (52.4%) but not necessarily the real break-even at -134 (about 57%). Points (55.3%, interval about 51 to 59.7%) cannot be told apart from break-even.
- Rebounds made 76% of all profit. Monthly cells are tiny (100% and 0% months are a few bets).
- "Over 70% confident" but 60% realized: the probabilities are overconfident (poorly calibrated). The 70% cutoff was probably picked by looking at results, so treat the 60% as optimistic.
- The author's claim that books want 50/50 betting action is a common myth; books move lines on sharp money and do not need balance.
- The injury point: using who actually played as a feature is leakage; ignoring it and then filtering afterward is reasonable. Note the useful angle is the line not yet reacting to a teammate being out.

## Takeaways for us
1. Calibration check: when our models say an edge or probability, compare it to what actually happens by bucket. Add to checklist (section A).
2. Choose any confidence cutoff on one season and test it on the next. Never report the tuned cutoff's in-sample result.
3. Report profit with odds actually paid, per market, with intervals (ties in with the bootstrap item).
4. Props are where small-model edges are claimed; we do not model them. Not adopting now.
