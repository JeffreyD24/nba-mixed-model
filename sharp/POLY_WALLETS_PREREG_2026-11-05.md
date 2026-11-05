# Pre-registration: do Polymarket "sharp" wallets keep winning? (Nov 5, 2026)

Written and pushed BEFORE the full Polymarket trade history is downloaded (only a 4-game-per-league test pull exists at this
commit). Git history is the proof. Code: `sharp/wallet_rankings.py` (rankings), follow-test grader to be written to exactly this spec.

## Data
Polymarket game markets (moneyline, spreads, totals), every fill with wallet, side, size, price, time
(`sharp/exchange_history.py poly`, data-api v2 trades, both sides of each fill). Pre-game fills only. Resolved markets only.
- NBA 2025-26 (series 10345), NHL 2025-26 (10346), NCAA men's basketball 2025-26 (10470): RANK period = games before
  2026-01-15; TEST period = games 2026-01-15 to 2026-06-30 (regular season + playoffs).
- NFL 2025 (series 10187): RANK = games before 2025-11-15; TEST = games 2025-11-15 to 2026-02-15.
- The 2026-27 seasons (games after 2026-07-01, including NFL series 12185 and CFB 12756) are NOT part of this test (RULE 2);
  they are a running check only.

## Sharp wallet definition (fixed now, chosen only from the RANK period, per league)
Primary: 30+ markets in that league, $2,000+ pre-game money at risk, and CLV t-stat >= 2.0 (CLV = their fill price vs the last
pre-game price of the same token, weighted by money at risk; t-stat across their markets).
Secondary lists, reported but not the pass/fail test: top 20 by profit (30+ markets) and top 20 by accuracy (30+ markets).

## Follow rule (TEST period)
For each test market: every primary-sharp wallet with a non-zero net pre-game position gives a signal for its side.
Several sharps on the same side = one bet; sharps on both sides = no bet. 1 unit per bet.
Entry price = that wallet's own money-weighted pre-game price on that side + 1 cent (what a follower could plausibly get),
also reported at the closing (last pre-game) price. Profit per unit = won / entry - 1.

## Reported
Bets, units, ROI, CLV, win rate: per league, per market type, pooled; 90% bootstrap interval by game.
Baselines: the same rule with (a) the secondary profit list, (b) the accuracy list, (c) random wallets matched on number of
markets and money (200 draws).

## Pass / fail
PASS (worth building a live follow alert): pooled ROI at entry+1c > 0 AND CLV > 0 AND the 90% interval lower bound of ROI > 0
AND the primary list beats the random-wallet baseline's 95th percentile. ROI > 0 without the interval = LEAD only.
Anything else = FAIL, recorded as such. No changes to the definition after seeing TEST results; any new variant is a new
pre-registration graded on a later period or the other leagues.
