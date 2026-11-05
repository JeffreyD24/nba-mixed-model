# Sharp money signals: pre-registration (Nov 5, 2026)

Pushed before any signal is graded. Plan: betting-goals `SHARP_MONEY.md`. Data: `sharp/data/{sport}_splits.csv.gz` (`sharp/backfill_splits.py`),
Action Network's archive, 2019-20..2025-26 for NBA, NHL, NFL, NCAAM, college football. Seasons: **discovery 2019-20..2022-23,
holdout 2023-24..2025-26** (the current season is not used).

**Timing caveat (decides how results may be used):** the archive keeps one split per game, the final one before tip (about the close).
Anything graded against the OPENER with this split uses information from later in the day: descriptive only ("were sharps right?"), never a
bet rule. Bet rules can only be graded at the CLOSE (the split is available then).

## Signals (fixed)
- **Money-ticket gap** on the home spread side and on the over: G = money % - bets % (Consensus). **Sharp side** = the side with G >= +10
  (the other side has G <= -10 by construction).
- **Reverse line move (RLM):** the line moved from the Open book to DraftKings' last line by >= 1 pt (spread) / 1.5 pts (total) toward the side
  with fewer than 50% of the bets.

## Questions
- **Q1 (descriptive): were sharps right?** Sharp-side cover rate vs the opener and vs the close; RLM side the same. By sport.
- **Q2 (bet rule, at the close):** bet the sharp side (G >= 10) at the close. Discovery qualifies a sport x market if cover >= 52.4% with z >= 2.0;
  holdout PASS = same direction >= 52.4%, z >= 1.65. Same for RLM. PASS -> PROVISIONAL candidate (Fable review); FAIL -> recorded.
- **Q3 (do sharps see what our model doesn't?):** NBA totals v4 (3+ vs DK opener, 2023-26) and NCAAM totals M2 / spreads ENS (2023-26): split our
  bets into sharp-agrees / sharp-disagrees / no signal; win rate and units at the opener and at the close in each. Descriptive (2023-26 already
  used for those models).
- **Q4 (does the signal add information the close lacks?):** regress result - close on (our model - close) and G, all games 2023-26 with a model
  prediction: G's slope and t. G > 0 with t > 2 = money split carries information beyond the close.
