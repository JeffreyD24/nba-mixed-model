# Polymarket US paper trades (NBA)

Updated 2026-11-02 11:37 ET by `polymarket.py --grade`. Nothing here was actually bet: these are the trades the model would have made on Polymarket US. 1 unit = $1 spent (price plus fee). Taker = bought at the best offer; maker = a limit bid at the highest price with 5%+ expected value, counted as filled if the best offer later fell to it before the game (approximate). CLV = the side's last mid price before the start minus the price paid, in cents (positive = the market moved toward us).

| model | market | kind | trades | W-L | units | ROI | avg EV at entry | avg CLV (cents) |
|---|---|---|---|---|---|---|---|---|
| model | moneyline | taker | 2 | 1-1 | +0.49 | +24.4% | +14.6% | +1.00 |

Limit orders: 2 of 2 filled before the game.

Same bet at DraftKings at the moment of the trade (same line): Polymarket was cheaper on 100% of 6 taker trades (average +1.6 cents per $1 contract in Polymarket's favor).

Waiting to be graded: 10. Open limit orders: 1.

Contracts or events the tracker couldn't read: 8 (see `research/polymarket/unmatched.csv`).
