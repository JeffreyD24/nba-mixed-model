# Bail-out alerts for logged bets: results and what went live (Nov 4, 2026)

Pre-registration: `analysis/BAILOUT_PREREG.md` (commit f8364f0; addendum after results at the bottom). Code: `analysis/bailout_test.py`;
output `analysis/bailout_test_output.txt`; thresholds `analysis/bailout_thresholds.csv`. Reviewed by Fable twice (fixes applied).

Opener bets with edge 3+, DraftKings 2023-26. At the FIRST snapshot the line is k+ pts against the bet (no hindsight):

| Market | k | Bets | Ride win% | Break-even cash-out (per $1 staked) | Hedge (other side at that line) win% |
|---|---|---|---|---|---|
| Totals | 1 | 780 | 51.2% | 0.98 | 45.7% |
| Totals | 2 | 494 | 49.1% | 0.94 | 45.2% |
| Totals | **3** | 308 | **45.0%** | **0.86** | 47.2% |
| Totals | **4** | 163 | **39.5%** | **0.76** | 52.2% |
| Spreads | **1** | 166 | **45.1%** | **0.86** | 52.4% |
| Spreads | **2** | 55 | **33.3%** | **0.64** | 63.6% |

## Live (PROVISIONAL)
`bailout.py`, run inside every alert check. When the DraftKings line moves 3+ / 4+ pts against a logged total, or 1+ / 2+ pts against a
logged spread (measured from the DraftKings line when the bet was logged), one phone alert per tier: cash out only if offered at least
X% of the stake (from the table, adjusted for the logged price); otherwise let it ride. Hedge suggested only for spreads at 2+ (55 bets).
Sent 4 AM-8 PM ET; never after tip. Log: `state/bailout_alerts.csv`.

## Personal note / takeaways
- Small moves against don't justify bailing on totals: bets that moved 1-2 pts against still won about half the time.
- Cashing out is a bet the other way with the book's cut. DraftKings' offers aren't recorded, so the alert gives the break-even; if the
  offer is below it, riding has been worth more. Note the offers you see in your bet's notes so we can learn how they are priced.
- Spreads turn bad faster than totals (one point is enough), matching the line-move test.
- All in-sample for the model's bet set; refit monthly with 2026-27 live data.
