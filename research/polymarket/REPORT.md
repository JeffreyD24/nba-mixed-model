# Polymarket US paper trades (NBA)

Updated 2026-11-04 18:18 ET by `polymarket.py --grade`. Nothing here was actually bet: these are the trades the model would have made on Polymarket US. 1 unit = $1 spent (price plus fee). Taker = bought at the best offer; maker = a limit bid at the highest price with 5%+ expected value. maker (strict) = the best offer later dropped below our price before the game, so we would have been filled; maker (touch only) = the offer only reached our price, so a fill is not certain (sellers may have traded with bids ahead of us); maker (old rule) = logged before Nov 4, 2026, when any touch counted. Judge limit orders on the strict rows. CLV = the side's last mid price before the start minus the price paid, in cents (positive = the market moved toward us).

| model | market | kind | trades | W-L | units | ROI | avg EV at entry | avg CLV (cents) |
|---|---|---|---|---|---|---|---|---|
| model | moneyline | maker (old rule) | 2 | 2-0 | +2.17 | +108.5% | +7.1% | +7.50 |
| model | moneyline | taker | 17 | 8-9 | -1.54 | -9.0% | +19.6% | +0.50 |

Limit orders: 25 of 26 reached our price before the game. Since the stricter rule (Nov 4, 2026): 0 of 0 filled for certain (offer dropped below our price), 0 only touched it.

Same bet at DraftKings at the moment of the trade (same line): Polymarket was cheaper on 80% of 20 taker trades (average +1.4 cents per $1 contract in Polymarket's favor).

Waiting to be graded: 42. Open limit orders: 19.

## Order book depth (books saved in the last 7 days)

Contracts you could buy on the long side within 1 / 3 / 5 cents of the best offer, and the extra cost of buying 1,000 and 5,000 contracts by walking the book (median cents above the best offer). Split by when the book was seen: on the game's own date versus days ahead, since the early books are much thinner. Full levels are in `research/polymarket/book_YYYY-MM-DD.csv`.

| market | when | snapshots | within 1c | within 3c | within 5c | 1,000: extra cents | 5,000: extra cents | deep enough for 5,000 |
|---|---|---|---|---|---|---|---|---|
| moneyline | days ahead | 8497 | 200 | 1058 | 1395 | +2.6 | +14.1 | 100% |
| moneyline | game day | 902 | 550864 | 644868 | 659969 | +0.0 | +0.0 | 100% |

Contracts or events the tracker couldn't read: 25 (see `research/polymarket/unmatched.csv`).
