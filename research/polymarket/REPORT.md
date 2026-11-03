# Polymarket US paper trades (NBA)

Updated 2026-11-03 11:30 ET by `polymarket.py --grade`. Nothing here was actually bet: these are the trades the model would have made on Polymarket US. 1 unit = $1 spent (price plus fee). Taker = bought at the best offer; maker = a limit bid at the highest price with 5%+ expected value, counted as filled if the best offer later fell to it before the game (approximate). CLV = the side's last mid price before the start minus the price paid, in cents (positive = the market moved toward us).

| model | market | kind | trades | W-L | units | ROI | avg EV at entry | avg CLV (cents) |
|---|---|---|---|---|---|---|---|---|
| model | moneyline | maker | 2 | 2-0 | +2.17 | +108.5% | +7.1% | +7.50 |
| model | moneyline | taker | 17 | 8-9 | -1.54 | -9.0% | +19.6% | +0.50 |

Limit orders: 16 of 17 filled before the game.

Same bet at DraftKings at the moment of the trade (same line): Polymarket was cheaper on 92% of 13 taker trades (average +1.9 cents per $1 contract in Polymarket's favor).

Waiting to be graded: 20. Open limit orders: 7.

## Order book depth (last 3 days of saved books)

Contracts you could buy on the long side at the best offer plus 1 / 3 / 5 cents, and what it would cost to buy 1,000 contracts (about $300-700) by walking the book: average price above the best offer, in cents, and how often the book was deep enough. Full levels are in `research/polymarket/book_YYYY-MM-DD.csv`.

| market | snapshots | within 1c | within 3c | within 5c | 1,000 contracts: extra cents | deep enough for 1,000 |
|---|---|---|---|---|---|---|
| moneyline | 3186 | 256 | 1444 | 1896 | +2.0 | 100% |

Contracts or events the tracker couldn't read: 23 (see `research/polymarket/unmatched.csv`).
