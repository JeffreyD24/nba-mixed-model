# Polymarket US paper trades (NBA)

Updated 2026-11-07 11:15 ET by `polymarket.py --grade`. Nothing here was actually bet: these are the trades the model would have made on Polymarket US. 1 unit = $1 spent (price plus fee). Taker = bought at the best offer; maker = a limit bid at the highest price with 5%+ expected value. maker (strict) = the best offer later dropped below our price before the game, so we would have been filled; maker (touch only) = the offer only reached our price, so a fill is not certain (sellers may have traded with bids ahead of us); maker (old rule) = logged before Nov 4, 2026, when any touch counted. Judge limit orders on the strict rows. CLV = the side's last mid price before the start minus the price paid, in cents (positive = the market moved toward us).

| model | market | kind | trades | W-L | units | ROI | avg EV at entry | avg CLV (cents) |
|---|---|---|---|---|---|---|---|---|
| model | moneyline | maker (old rule) | 8 | 6-2 | +2.43 | +30.4% | +6.6% | +2.38 |
| model | moneyline | maker (strict) | 2 | 0-2 | -2.00 | -100.0% | +7.9% | +6.50 |
| model | moneyline | taker | 38 | 16-22 | -5.87 | -15.5% | +20.6% | +0.79 |
| model@early | moneyline | maker (old rule) | 15 | 12-3 | +5.89 | +39.2% | +6.0% | -1.97 |
| model@early | moneyline | maker (strict) | 1 | 1-0 | +0.39 | +38.9% | +5.9% | -13.50 |
| model@early | moneyline | taker | 8 | 3-5 | -1.61 | -20.1% | +25.3% | -0.12 |

Limit orders: 41 of 48 reached our price before the game. Since the stricter rule (Nov 4, 2026): 8 of 9 filled for certain (offer dropped below our price), 1 only touched it.

Same bet at DraftKings at the moment of the trade (same line): Polymarket was cheaper on 76% of 25 taker trades (average +1.5 cents per $1 contract in Polymarket's favor).

Waiting to be graded: 33. Open limit orders: 15.

## Order book depth (books saved in the last 7 days)

Contracts you could buy on the long side within 1 / 3 / 5 cents of the best offer, and the extra cost of buying 1,000 and 5,000 contracts by walking the book (median cents above the best offer). Split by when the book was seen: on the game's own date versus days ahead, since the early books are much thinner. Full levels are in `research/polymarket/book_YYYY-MM-DD.csv`.

| market | when | snapshots | within 1c | within 3c | within 5c | 1,000: extra cents | 5,000: extra cents | deep enough for 5,000 |
|---|---|---|---|---|---|---|---|---|
| moneyline | days ahead | 18353 | 241 | 935 | 1251 | +2.7 | +15.9 | 99% |
| moneyline | game day | 2561 | 430988 | 505654 | 524013 | +0.0 | +0.0 | 100% |

Contracts or events the tracker couldn't read: 56 (see `research/polymarket/unmatched.csv`).
