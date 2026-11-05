# NBA prop unders at the best book — pre-registration (written Nov 5, 2026, before any results on these seasons)

## Why
The props v1 test found every book's prop close leans to overs (no-vig over 49.0–49.6% vs overs hitting 47.5–48.8%, 2025-26), but a
blind under at ONE book still loses to the vig (−3.7% to −4.4%). Shopping four books might close that gap.

## Data
`data/props_history/bettingpros/` (BettingPros public API: each book's last line + price before the game, and the opener), points,
rebounds, assists, threes. Results: `data/player_stats/` box scores (players who don't play are void).

## Rule (fixed now)
- For each game × player × stat: the closing under at DraftKings, FanDuel, BetMGM and Caesars, using only lines updated within
  6 hours before the scheduled tip (older ones are treated as stale/not offered).
- Bet the under at the book with the **highest line**; ties → best price. 1 unit. One bet per player-stat-game.
- Bet time = just before tip (these are closing lines), so closing-line value is ~0 by construction and **units are the measure**.

## Seasons
- **Primary (unseen): 2022-23, 2023-24, 2024-25.**
- Descriptive only: 2021-22 (DraftKings only), 2025-26 (where the over-lean was first noticed), 2026-27 to date.

## Pass (both needed)
1. Pooled ROI over the three primary seasons > 0 with a 90% bootstrap CI (by date) above 0.
2. ROI > 0 in at least 2 of the 3 primary seasons.
A pass goes live only as PROVISIONAL (own record), after a Fable check.

## Descriptive
By stat, by line size, by book chosen, single-book versions (DK only, FD only), favourite vs underdog game, how often the best
under is a higher line vs only a better price, and the over-lean (no-vig consensus vs actual) by season.

## Amendment (Nov 5, 2026, ~12:15 ET) — before any PRIMARY-season result
Plumbing check on the non-primary 2025-26 tail / 2026-27 files: BettingPros stamps its final pre-game capture at or just after the
scheduled tip (89% of lines are stamped 0–14 minutes after tip; none later than 14 minutes). The "within 6 hours before tip" filter
would have thrown nearly all closes away. Fixed rule: a line counts if stamped **between 6 hours before and 15 minutes after** the
scheduled tip. (Only the two descriptive seasons had been computed when this was found; they're re-run under the same fix.)
