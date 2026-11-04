# Hedge / middle system: results (Nov 4, 2026)

Pre-registration: `analysis/MIDDLES_PREREG.md` (commit 8f5f799). Code `analysis/middles_test.py`; output `analysis/middles_test_output.txt`;
every opportunity `analysis/middles_opps.csv`. Fable review: the first run's only qualifying cell (CT totals, gap 2.5+, +4.4u) came from
3 bad quotes (gaps of 10-19 pts, one an in-game line let through by a moved tip). Fixed (first recorded tip; gaps of 8+ dropped).

## Bottom line: no hedge or middle alert. Nothing went live.
- **Middling our own bets (B): costs money at every move size.** The other side at the moved line won only 44-48% (totals -43u to -146u,
  spreads -17u to -34u, negative every season). Riding alone beat ride + hedge in every bucket. It only lowers the swings.
- **Book-gap middles at the CT books (DraftKings + FanDuel): negative at every gap size** (totals 2.5+: 174 games, middle hit 3.4%,
  -1.0u; spreads 2.5+: -7.8u). Fails the pre-registered rule.

| Book group (info) | Totals, gap 2.5+ | Spreads, best gap |
|---|---|---|
| CT (DK + FD) | 174 games, -1.0u, 2/5 seasons + | all negative |
| US regulated (DK, FD, BetMGM, Caesars, BetRivers) | 756 games, +8.6u (+1.1 per 100 pairs), 4/5 seasons + | 1.5+: +4.9u, 3/5 |
| All 10 incl. offshore | 2,282 games, +80.8u (+3.5 per 100), 5/5 seasons + | 1.5+: +86.5u, 4/5 |

The only real middle value is with offshore books (not legal for Jeffrey) and, barely, across 5 US books after he leaves Connecticut.
Hourly snapshots make all of this an upper bound: only about a third of 2.5+ gaps were still there an hour later.

## Personal note / takeaways
- A hedge is a second bet; it only pays if that bet would be worth making on its own. Ours never are, because the model still beats the
  moved line. The one exception kept: the bail-out alert's spread 2+ pt hedge (provisional, 55 bets).
- More books = more middles. Worth revisiting the US-regulated totals 2.5+ middle when he moves out of CT (live check first: Action
  Network data shows FanDuel lines can sit stale in the recorder, so a live alert would need a fresh fetch before alerting).
