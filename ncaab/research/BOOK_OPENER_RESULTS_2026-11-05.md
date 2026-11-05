# NCAAM at real sportsbooks' own openers: results (Nov 5, 2026)

> **CORRECTION (Nov 5, afternoon): the spreads PASS below was caused by bad data.** 375 ESPN openers (2.6%) have the sign flipped
> (e.g. -4 stored as +4: opposite sign to both DraftKings' close and Action Network's Open). A flipped quote makes a fake ~8-pt edge
> that "wins"; 92 of the 712 bets were on them. Excluding them: **all books 620 bets 51.6%, -8.8u, CLV +0.65 (break-even 0.67);
> DraftKings only 313 bets 50.8%, -9.2u, CLV +0.62. FAIL.** NCAAM has no edge at a bettable line. The daily TEST record now drops
> flipped quotes. (College football at book openers already failed; flips would only have flattered it.)

Pre-registration `ncaab/research/BOOK_OPENER_PREREG_2026-11-05.md`; code `ncaab/book_opener_test.py`; output `ncaab/research/book_opener_output.txt`.
Openers from ESPN's free odds feed (`ncaab/espn_openers.py`): DraftKings 2023-24 and 2025-26, ESPN BET 2024-25 (and gaps). 14,497 eligible games.
Unlike college football, the books' own openers sit close to Action Network's "Open" here (0.64 pts spreads, 0.56 totals on average).

| Market / model | At AN "Open" (before) | At the book's own opener | Rule |
|---|---|---|---|
| Spreads M1 (5+) | 629 bets, -11.1u, CLV +0.84 | **712 bets 54.3%, +26.2u, CLV +1.48** (24 +1.2, 25 +24.6, 26 +0.4) | PASS |
| Spreads M5 (5+) | 649 bets, +2.2u | 734 bets, +8.8u, CLV +1.44 (26 -16.8) | FAIL |
| Totals M1 (6+) | 1,148 bets, -6.2u | 1,127 bets, +0.6u, CLV +0.91 (b/e 0.99) | FAIL |
| Totals M5 (6+) | 612 bets, +0.9u | 648 bets, -17.0u | FAIL |

**Split by book (spreads M1):** DraftKings only 348 bets 179-162, **+0.7u, CLV +1.26** (break-even 0.67); ESPN BET 2024-25 256 bets 57.4% +24.6u.
Most of the units come from ESPN BET (not offered in Connecticut). At DraftKings the line moves our way by nearly twice break-even, but
units are flat (348 bets: luck alone moves ROI about +/-5%).

## Decision
- Passes the written rule, but not live: the profit is mostly at a book Jeffrey can't use, and the DraftKings-only units are flat. Per the
  pre-registration nothing goes live without a further written test and a Fable review.
- From today the NCAAM daily TEST record also grades the spreads rule at DraftKings' own opener (else ESPN BET) each morning
  (`ncaab/daily.py`), so 2026-27 builds the DraftKings sample. Candidate for PROVISIONAL if DraftKings-only CLV stays at or above +0.67
  and units turn positive over the first ~150 bets.
- NBA, NHL and NFL backtests already used DraftKings' own first line (The Odds API snapshots, pinned to ~10 minutes after posting): not affected.
