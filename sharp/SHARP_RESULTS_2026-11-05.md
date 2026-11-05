# Sharp money signals: results (Nov 5, 2026)

Pre-registration `sharp/SHARP_PREREG_2026-11-05.md`; code `sharp/signals_test.py`; full output `sharp/signals_output.txt`.
Data: Action Network archive, 61,980 games with final money splits, 2019-20..2025-26, five leagues (`sharp/backfill_splits.py`).
Note: the Open book exists only from 2023-24, so everything "vs the opener" and the reverse-line-move signal are holdout-only and descriptive.

## Q2: betting the sharp side at the close: FAIL everywhere (no cell qualified)
Sharp side (money % - bets % >= 10), cover rate vs the close, holdout 2023-26: NBA spread 50.1%, NBA total 52.7% (z +1.6), NHL total 49.9%,
NFL spread 52.0%, NFL total 52.5%, NCAAM spread 49.8%, NCAAM total 50.6%, college football spread 50.2%, total 52.0% (discovery 52.4%, z +2.2,
just under the 52.4% bar). Reverse line moves vs the close: 48.9-51.2%.
## Q1 (descriptive, uses near-tip splits): sharps were right vs the opener
Sharp side vs the opener 50.8-58.9%; reverse-line-move side 56.5-62.1%. The money gap correlates with the open-to-close move (NFL totals +0.34,
college football totals +0.26, NBA spreads +0.16, NCAAM spreads +0.14): the money is what moves the line.
## Q4: the final split adds nothing beyond the close
result - close on (model - close) + gap: gap slope t +1.0 (NBA totals), -0.3 (NCAAM totals), +0.1 (NCAAM spreads). By tip-off it is priced in.
## Q3: when sharp money disagrees with our model
| Our bets | Sharps agree | Sharps disagree | No strong signal |
|---|---|---|---|
| NBA totals v4 (3+) | 206 bets 55.8% +13.5u (close 52.0%) | **197 bets 49.7% -9.8u (close 46.9%, -20.4u)** | 1,248 bets 57.1% +113.3u |
| NCAAM totals M2 (6+) | 97 bets 56.2% +7.1u | 93 bets 53.3% +1.5u | 460 bets 52.0% -3.7u |
| NCAAM spreads ENS (5+) | 89 bets 60.5% +13.3u (close 58.4%) | 100 bets 55.0% +5.0u | 324 bets 53.7% +8.3u |
Our NBA totals bets that the big money opposes lose. But the split used is from near tip-off, after our opener bet.

## What it means and what runs now
- Sharp money is not a free signal at the close: by then it is in the line. Its value is TIMING (being on the side the money will hit before it
  moves the line) and as a WARNING on our own bets. Both need to know when the money arrives, which the archive does not keep.
- **Live tracker started** (`sharp/live_capture.py`, workflow `sharp-live.yml`, every 10 min, all five leagues): splits + DraftKings, FanDuel,
  Open, Consensus lines with timestamps, and per-game signals (gap and when it first hit 10, DraftKings move, reverse line move, steam).
  Recorded only. Sharp books (Pinnacle, Circa, BetOnline...) are not returned live by Action Network; Pinnacle comes from `pinnacle_watch.py`.
- Historical WHEN is still possible for lines (not money): The Odds API hourly multi-book snapshots 2020-26 (`data/odds_history`, includes
  Pinnacle) can test "Pinnacle moves first, DraftKings follows" on past seasons. That is the next test.
