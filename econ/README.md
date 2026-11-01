# Economics contracts research (started Nov 1, 2026)

Question: can free public forecasts beat Kalshi's prices on economic-data contracts? (Kalshi stands in for DraftKings
Predictions, which has no public price feed. Research only; nothing here trades.)

## Data (`econ/data`, downloaded by the "Economics history download" workflow; all public, no keys)
- `kalshi_markets.csv`: every settled contract in KXCPI, KXCPICORE, KXCPIYOY, KXPAYROLLS, KXU3, KXFEDDECISION, KXFED, KXGDP
  (2021 to Oct 2026), with strike, settlement value and result.
- `kalshi_hourly.csv.gz`: hourly best bid / ask / last price and open interest for the 15 days before each contract closed.
- `cleveland_nowcast_*.json.gz`: Cleveland Fed inflation nowcast history (daily, since 2013), with actuals.
- `gdpnow.xlsx`: Atlanta Fed GDPNow workbook (daily nowcast history since 2011, track record).

## Method (`backtest_cpi.py`, `backtest_gdp.py`)
At 7 days, 3 days, 1 day, 6 hours and 1 hour before Kalshi closes each release: Kalshi's bid/ask for every "Above X%"
contract vs a probability from the forecast published the day before, using the forecast's own past misses at the same
distance from the release (walk-forward, only releases already out) with the 0.1 rounding built in. Paper trade when expected
value after Kalshi's taker fee (7% x p x (1 - p)) is 5%+. Skips contracts under 5 cents or over 95, or with a spread over 10 cents.
Graded on Kalshi's settlement.

## Results (Nov 1, 2026)
- **CPI (headline and core, month over month), 64 months:** no edge. Kalshi's prices were more accurate than the nowcast at
  every horizon (Brier about 0.11-0.15 vs 0.14-0.20), and mixing in the nowcast made them worse except a week out.
  Paper trades: -0.6% overall (35 months up, 29 down; 90% bootstrap range -14.5% to +12.7%). The model claimed +70-90%
  expected value per trade, so the market already has what the nowcast knows and more.
- **GDP (advance estimate), 16 quarters, 139 trades:** +19.3%, but the 90% range is -15.5% to +43.4%, 10 quarters up and 6
  down, and one quarter made 59% of the profit. GDPNow was about as accurate as the market. Too few releases to tell; worth
  watching, not betting.
- Not tested: jobs and unemployment (no free forecast to compare with), Fed decisions (the market is the forecast).
