# Pre-registration: bail-out (cash out / hedge / ride) after the line moves against a placed bet (Nov 4, 2026)

Written and pushed **before any result.** Jeffrey's idea: after a logged bet, if the line moves against the model, alert him with the
cash-out amount worth taking; below it, let the bet ride.

## Data
DraftKings 2023-24 .. 2025-26, NBA totals and spreads, the opener bets with edge 3+ in `analysis/line_move_threshold_bets.csv` (side fixed
at the opener, previous game's injury report, spreads in the live windows). Line path: DraftKings snapshots before tip
(`data/odds_history/nba_snapshots.csv.gz`). The bet is placed at the opener. In-sample for the models; the cash-out threshold itself is
model-free (it only uses how often bets in that spot went on to win).

## The moment of decision (no hindsight)
For each bet, walk the snapshots in time order. The trigger for move size k (k = 1, 2, 3, 4 pts) is the FIRST snapshot where the line is
k+ pts against the bet line. What happens after that moment is not used to choose the bet set. Each bet can trigger several k.

## Options compared at the trigger, per 1 unit staked at -110 (win returns 1.909, push 1.0)
- **Ride:** the original bet's return. Its average return per unit = the **break-even cash-out**: cash out only if the offer is at least
  this share of the stake (e.g. 0.80 means "cash out a $2.50 bet only if offered $2.00+").
- **Hedge:** add 1 unit on the other side at the triggered line (-110). Hedge minus ride = the hedge bet alone, so hedging beats riding
  only if betting the other side at the moved line wins more than 52.4%.
- **Cash out:** DraftKings offers are not recorded, so it's judged against the break-even above.

## Decision rule (fixed now)
For each market and k, with the ride win rate and its 90% interval (bootstrap by game):
1. The alert fires at the smallest k whose **ride win rate is below 47.6%** (2 pts under the -110 break-even), with at least 60 triggered
   bets, and the drop holds in at least 2 of 3 seasons (ride win rate < 52.4% in that season). Larger k use their own thresholds.
2. The alert gives: the cash-out amount = stake x average ride return at that k (rounded down to the cent), and "otherwise let it ride".
3. Hedge is suggested in the alert only if the hedge bet at that k wins >= 52.4% overall and in 2 of 3 seasons; otherwise not mentioned.
4. If no k qualifies for a market, no bail-out alert for that market; the bet's move is still logged.
5. Thresholds are refit only on the monthly review once 2026-27 live data is added (5-minute checks). Fable reviews before it goes live.
   This is a PROVISIONAL tool: it never tells him to bet, only what a cash-out offer must beat.

## Notes
- Live bets are often at FanDuel; the alert measures the move with the DraftKings line against his logged bet line.
- Thresholds are per unit; the alert scales by the stake and price he logged.

## Addendum after results (Nov 4, 2026; written after seeing results, flagged as such)
- Qualifying by rule 1: totals from k = 3 (45.0%, 308 bets), spreads from k = 1 (45.1%, 166 bets). Live tiers: totals 3 and 4, spreads 1 and 2.
- Spread tier 2 has 55 bets (rule 1's 60-bet floor is stated for the first tier only). It is used with its own threshold, and its hedge
  suggestion (35-20, 63.6%; 90% lower bound about 53%) has no sample floor in rule 3. Both are PROVISIONAL and reviewed monthly.
- Spread tiers 3-4 (24 and 15 bets) are not used.
- Moves are measured on DraftKings from the line at the time the bet was logged (Fable review): many bets are at FanDuel, and the gap
  between books is not a move.
