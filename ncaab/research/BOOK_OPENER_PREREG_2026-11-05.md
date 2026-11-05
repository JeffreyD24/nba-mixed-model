# NCAAM at real sportsbooks' own openers: pre-registration (Nov 5, 2026)

Pushed before grading. The NCAAM Model 1 backtest, conference-totals lead and tournament were graded from Action Network's "Open"
book, which college football showed is an earlier, softer number than any book we can bet (nfl-mixed-model
`ncaaf/research/BOOK_OPENER_PREREG_2026-11-05.md`). Re-grade at named books' own openers from ESPN's free odds feed
(`ncaab/espn_openers.py`): **DraftKings** (2023-24, 2025-26) and **ESPN BET** (2024-25 and wherever DraftKings is missing).
- Models and rules unchanged, no new choices: Model 1 (spreads 5+, totals 6+) and the tournament winner M5 (same thresholds), same
  filters (both D-I, neutral flag unambiguous, both teams 3+ games). -110. Bad quotes dropped: opener more than 10 pts (spread) /
  15 pts (total) from DraftKings' close.
- Measures: CLV = that opener to DraftKings' close (break-even 0.67 spreads, 0.99 totals); units at that opener; by season.
- PASS = CLV >= break-even and units > 0 and no season below -5u. Nothing goes live either way without a further written test and a
  Fable review; this decides whether NCAAM has any edge at a bettable number.
