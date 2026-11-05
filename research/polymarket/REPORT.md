# Polymarket US paper trades (NBA)

Updated 2026-11-05 11:40 ET by `polymarket.py --grade`. Nothing here was actually bet: these are the trades the model would have made on Polymarket US. 1 unit = $1 spent (price plus fee). Taker = bought at the best offer; maker = a limit bid at the highest price with 5%+ expected value. maker (strict) = the best offer later dropped below our price before the game, so we would have been filled; maker (touch only) = the offer only reached our price, so a fill is not certain (sellers may have traded with bids ahead of us); maker (old rule) = logged before Nov 4, 2026, when any touch counted. Judge limit orders on the strict rows. CLV = the side's last mid price before the start minus the price paid, in cents (positive = the market moved toward us).

| model | market | kind | trades | W-L | units | ROI | avg EV at entry | avg CLV (cents) |
|---|---|---|---|---|---|---|---|---|
| model | moneyline | maker (old rule) | 6 | 4-2 | +0.92 | +15.3% | +6.7% | +3.50 |
| model | moneyline | taker | 29 | 13-16 | -2.78 | -9.6% | +20.0% | +0.26 |
| model@early | moneyline | maker (old rule) | 8 | 7-1 | +5.00 | +62.4% | +6.1% | -1.00 |
| model@early | moneyline | taker | 6 | 2-4 | -1.98 | -33.0% | +27.3% | +1.00 |

Limit orders: 29 of 33 reached our price before the game. Since the stricter rule (Nov 4, 2026): 0 of 0 filled for certain (offer dropped below our price), 0 only touched it.

Same bet at DraftKings at the moment of the trade (same line): Polymarket was cheaper on 77% of 22 taker trades (average +1.5 cents per $1 contract in Polymarket's favor).

Waiting to be graded: 19. Open limit orders: 12.

## Order book depth (books saved in the last 7 days)

Contracts you could buy on the long side within 1 / 3 / 5 cents of the best offer, and the extra cost of buying 1,000 and 5,000 contracts by walking the book (median cents above the best offer). Split by when the book was seen: on the game's own date versus days ahead, since the early books are much thinner. Full levels are in `research/polymarket/book_YYYY-MM-DD.csv`.

| market | when | snapshots | within 1c | within 3c | within 5c | 1,000: extra cents | 5,000: extra cents | deep enough for 5,000 |
|---|---|---|---|---|---|---|---|---|
| moneyline | days ahead | 11078 | 215 | 1002 | 1328 | +2.6 | +14.2 | 99% |
| moneyline | game day | 1170 | 547868 | 640538 | 645179 | +0.0 | +0.0 | 100% |

Contracts or events the tracker couldn't read: 41 (see `research/polymarket/unmatched.csv`).
