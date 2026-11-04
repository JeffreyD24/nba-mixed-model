# Pre-registration: middles between books, and middling our own bets (Nov 4, 2026)

Written and pushed **before any result.** Two questions from Jeffrey's "hedge bet system" idea:
- **A. Book-gap middles:** when two books disagree on a total or spread by g+ pts at the same moment, betting the low over / high
  under (or favorite at the short number / underdog at the long number) wins both bets if the game lands in between. Does it pay?
- **B. Middling our own bets:** after our opener bet (DraftKings, edge 3+), when the line moves g+ pts toward the model, add the other
  side at the best moved line. Does the hedge leg pay, i.e. does the combined position beat riding alone?

## Data
`data/odds_history/nba_snapshots.csv.gz`, 2021-22 .. 2025-26 regular seasons, pre-tip snapshots taken at the same time for all books.
Prices are the real prices recorded; rows with a price outside -250..+200 are dropped as bad or live quotes. Finals from
`data/training_games.csv` (games without a final are dropped).

Book groups:
- **CT (decision set):** DraftKings and FanDuel (books Jeffrey can use now).
- **US regulated (info, for after he moves):** DraftKings, FanDuel, BetMGM, Caesars (williamhill_us), BetRivers.
- **All 10 books incl. offshore (info only).**

## A. Book-gap middles
For each game, market and gap size g (1, 1.5, 2, 2.5, 3+ pts), take the FIRST pre-tip snapshot where the best two lines in the group
differ by g+ (one opportunity per game, market and g, bet as first seen). Bet 1 unit on each leg at its own price.
Report: opportunities per season, middle hit rate, pushes, units per pair, units by season.

## B. Middling our own bets
Opener bets with edge 3+ from `analysis/line_move_threshold_bets.csv` (DraftKings 2023-26). At the first snapshot where the best CT line
on the other side is g+ pts better than our bet line (g = 1, 2, 3, 4), add 1 unit on the other side at that line and price.
Report: hedge leg alone (win %, units), combined position vs riding alone, middle hit rate, by season.

## Decision rule (fixed now)
- **A goes live as an alert** (CT books) for the smallest g where: at least 60 opportunities in 2021-26, units per pair > 0 pooled,
  and positive in at least 3 of 5 seasons. Otherwise no alert; US-regulated and offshore results are recorded for later.
- **B goes live as an alert suggestion** for the smallest g where the hedge leg's units > 0 pooled and in at least 2 of 3 seasons,
  with at least 60 hedges. Otherwise middling our own bets is not recommended (it only trades edge for lower swings).
- Anything that goes live is PROVISIONAL, reviewed monthly, checked by Fable first.

## Known limits
Snapshots are mostly hourly, so a gap may have lasted minutes (or been a stale quote) and not been bettable; limits on middles are
often low. Results are therefore an upper bound on what's achievable.
