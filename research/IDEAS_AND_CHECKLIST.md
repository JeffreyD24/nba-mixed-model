# Ideas from the Nov 3, 2026 web sweep, and the implementation checklist

Why this file exists: we searched GitHub, Reddit summaries, forums, pick-seller sites and papers for how other people beat (or fail to beat)
sports betting markets. This is the keeper: what we learned, what we already had, what we added, and what is left. Update the checkboxes
as work lands. Raw sources are listed at the bottom.

## What the evidence says (short version)
1. Settled lines are almost impossible to beat. The pro VSiN/Circa contest composite went 50.3% in 2024 (break-even is 52.4%).
   Edges live at openers and in soft markets (props, early lines), not late-week numbers.
2. The scoreboard is closing line value (CLV), not wins. Winning too early is luck; beating the close over 1,000+ bets is skill.
3. Winning gets you limited (about 10% of a fresh account's limit once flagged). Connecticut has only three books (DraftKings, FanDuel, Fanatics).
   The ceiling on profit is account limits, not model quality.
4. Every "verified" pick seller and Discord found was marketed through affiliate review sites; none had an independently checkable record. Do not pay for picks.
5. Claims that look too good (e.g. an NFL repo showing 91.9% spread wins) are leakage or bugs.

## Checklist (status as of Nov 3, 2026)
Legend: [x] already in place  [~] partly  [ ] open  (O) = good job for Opus

### A. Measure edge the right way
- [x] CLV in points on every logged bet, summarized in the NBA, NHL and NFL workbooks (average CLV, share of bets that beat the close)
- [x] Pinnacle and 9 other books recorded live (pinnacle_watch.py) and used as a sharp-book check in alerts
- [x] CLV in PRICE terms against Pinnacle's de-vigged close (points hide price moves, e.g. -110 to -125 with no point change). Done Nov 5: research/market_models/PRICE_CLV_RESULTS.md; live version in edge_stats.py
- [ ] Bootstrap (resample bets within each walk-forward season, ~1,000 draws) to put a confidence interval on ROI and CLV for every rule, and the share of draws that lose (idea from r/algobetting, see community_notes)
- [ ] Calibration table: group our predicted edges/probabilities into buckets and compare with realized results (the Reddit props author claimed 70%+ confidence and got 60%); choose any cutoff on one season and test it on the next
- [ ] Report CLV per model version and per bet rule next to the win/loss record, and set a decision rule up front
      (suggestion: judge a rule only after 300+ bets with average CLV; do not drop or promote one on win/loss alone)

### B. Shrink toward the market
- [x] NFL: late-season shrink toward the line already tested (analysis/nfl_fixes.py)
- [x] NBA: tested Nov 3, 2026 (analysis/market_shrink_test.py, results in analysis/FINDINGS.md). Against OPENING lines the model deserves about
      0.25 weight on its disagreement for spreads (+/-0.09) and 0.39 for totals (+/-0.10); against CLOSING lines about 0 (-0.06 and -0.13).
- [x] (Nov 3, 2026: shrunk_record.py, w = 0.147 / 0.318 with the one-day lag; research/SHRINK_WEIGHTS_2026-11-03.md) Add "Model 1 shrunk" as a side-by-side record (do NOT change Model 1; new version = new record, per your rule): shrunk number =
      line + w x (model - line) with w = 0.25 spreads / 0.39 totals, thresholds re-derived by backtest
- [ ] Same test as a regularized logistic/linear stack that takes model number AND market number as inputs, fitted on earlier seasons and scored on a later one (idea from the r/algobetting LLM thread; see community_notes)
- [x] (Nov 3, 2026: NHL 0.29 ML / 0.40 overs; NFL totals 0.55, spreads 0.06) Repeat the weight test for NHL and NFL (needs their walk-forward prediction files lined up with openers) (O: choosing thresholds without overfitting)

### C. Keep models simple
- [x] Three NBA models run side by side; none beat closing lines (research/model_comparison)
- [ ] Rule for adding factors: a new factor must improve out-of-sample CLV, not just in-sample fit. Log each test in analysis/FINDINGS.md

### D. Price vs consensus (Kaunitz et al.: bet prices that beat the de-vigged consensus)
- [~] Multi-book prices are already recorded (research/books, data/odds_history)
- [ ] Test whether best available price vs consensus at the opener predicts CLV in NBA/NHL/NFL. Needs a few months of snapshots; limits will cap it. (O)

### E. Free data
- [x] SportsbookReview 2011-2021 openers and closers, all four sports, cleaned and flagged (data/external/sbr, see its README)
- [ ] Out-of-sample test of the "bet at the opener" rules on 2011-2021 using the SBR openers (old_seasons.py currently grades closes only) (O)
- [ ] MLB: the SBR MLB file is stored for when the MLB model starts
- [x] hockeyR xG: code, fitted objects and a 2010-23 team-game xG table stored (data/external/hockeyr). Next: test it against SBR NHL openers (O)
- [x] NHL out-of-sample test vs SBR openers, 2016-17..2021-22 (Nov 3, 2026, nhl-mixed-model backtests/OOS_SBR_RESULTS.md): moneylines +1%/bet with
      negative CLV (not confirmed); overs at the opener +16.5%/bet and the total rose on 33.5% of picks vs 10.9% of all games (real signal)
- [~] BeatTheBookie: code stored; odds data is on Dropbox/Google Drive and needs your browser (data/external/beatthebookie/DOWNLOAD_LINKS.md)

### F. Audit for the classic failure modes
- [x] (Nov 3, 2026: research/LEAKAGE_AUDIT_2026-11-03.md) Independent leakage audit: timestamps of injury reports vs when openers were seen, any feature using information from after the bet time,
      training on closing lines, tuning thresholds on the test season (O: best done by Opus or a fresh pair of eyes)
- [x] (Nov 3, 2026: config/thresholds.csv + tools/check_thresholds.py) Place every threshold in one config file with the date and the data it was chosen on, so changes are visible

### G. Execution and limits
- [ ] Track which book each bet is placed at and the limit you were offered; log limit cuts the day they happen
- [ ] Plan for limits: decide what you do when DraftKings/FanDuel/Fanatics cap you (prediction markets once outside Connecticut)

### H. Communities (needs your browser)
- [x] Four r/algobetting threads read from your pastes ("Has anyone done it", NBA props season review, LLM bots, comments from a deleted post); notes in research/community_notes. Only new ideas: bootstrap intervals, calibration table, stack with the market; live-line overreaction parked
- [~] X public search done (research/community_notes). Reddit/4chan still open: re-do the sweep with the Claude desktop app browser or the Chrome extension (my shell cannot reach those sites)

## Open prop ideas (Nov 5, 2026)
- [ ] Props v2.1: minutes rescaled to 240/team, only new absences redistributed, each bet vs its own book, synchronized snapshots, 11 AM test.
- [ ] v1b at the OPENER on past seasons (BettingPros open_line/open_price, 2022-25; pre-register first): the past-season test of the
      morning edge (RULE 2: not the current season). The 11 AM FanDuel paper record is a pipeline check only.
- [ ] Model-selected unders (v2 unders +2.4/+7.9/+10.5/+8.1% in 2022-26; found after the fact): pre-register and test on 2021-22
      (DraftKings only) and leave-one-season-out, not on 2026-27.
- [ ] Same opener data: does the model predict the opener → close move (true CLV for props)?
- [ ] [LEAD] Props in April lose 3 of 4 seasons (−53u on 486 bets): test an end-of-season minutes fix (role changes, rest) on 2021-25.
- [ ] Re-fit var_ab on 2021-22 box scores only so 2023-24 becomes a clean test season for v1b at the opener.

## When to switch to Opus
Switch for: (1) the independent leakage audit, (2) choosing shrink thresholds and bet rules without overfitting, (3) any redesign of how
the three models are combined. Stay on Sonnet for: data downloads, cleaning, running backtests, logging, wiring alerts, reports.

## Sources
- VSiN/Circa contest write-up: figureitoutsportsbetting.substack.com/p/vsincirca-contest-showed-toughness
- r/algobetting summary: sportbotai.com/blog/sports-betting-model-reddit
- Simple-model backtest on SBR data: samesolutions-equipment-service.pages.dev/bets/learn/backtest-results.html
- Limits: howgamblingworks.substack.com/p/sportsbook-limits-get-a-closer-look; vixio.com (Connecticut operators)
- Consensus-price strategy: Kaunitz, Zhong, Kreiner, arXiv 1710.02824; github.com/Lisandro79/BeatTheBookie
- nfelo market regression: nfeloapp.com
- Data: github.com/FinnedAI/sportsbookreview-scraper

## Sharp money (Nov 5, 2026; sharp/SHARP_RESULTS_2026-11-05.md)
- [ ] Historical timing: does Pinnacle (Odds API hourly multi-book snapshots 2020-26) move before DraftKings, and does following its first move beat DK's opener? Pre-register.
- [ ] Early-money warning: once the live tracker has history, does a money gap >= 10 against our bet seen BEFORE the line moves predict our losers? (Lead: NBA totals v4 sharp-disagree 197 bets 49.7%.)
- [ ] Steam and reverse line moves from live data: which books move first, and how much of DK's move follows.
- [ ] Polymarket: follow large, historically profitable wallets in sports markets (public trade history with wallet ids).
- [ ] Replace the paid Pinnacle feed: record Kalshi + Polymarket + BetOnline (college) free; test their accuracy vs Pinnacle on past seasons with the saved Pinnacle history; then cut over the live Pinnacle uses.
- [ ] Polymarket wallets (data API v2): pull past sports trades, rank wallets by profit and closing-price edge, test following them out of sample.

- [ ] [LEAD, Nov 5 2026] NHL: rested team vs a back-to-back team wins more than the no-vig close implies (57.7% vs 55.3% 2016-22; 59.7% vs 55.8% 2024-26), CLV ~0. Pre-register a moneyline rule (opener and close, units + "won vs no-vig close"), test on SBR 2011-16 (not used to find it), then PROVISIONAL. research/PROVISIONAL_CANDIDATES_2026-11-05.md
- [x] [IDEA, Nov 5 2026] NFL 2H totals are bet with money without a provisional row: pre-register and measure CLV, or stop. DONE: failed (2023 -15.4u), alerts stopped.
- [ ] [IDEA, Nov 5 2026] Market models step 6: copy the opener/movement/blend setup to NBA spreads, then NHL and NFL (needs the reachability filter from day one).
- [ ] (Nov 5, 2026) Polymarket sharp-wallet follow test: download full 2025-26 trade history into the private repo, run `sharp/wallet_rankings.py --before 2026-01-15`, grade per `sharp/POLY_WALLETS_PREREG_2026-11-05.md`.
- [ ] (Nov 5, 2026) Kalshi history (candles + trades with sizes) into the private repo; test Kalshi/Polymarket close vs DK close and vs saved Pinnacle history (NHL veto replacement).
- [ ] (Nov 5, 2026) Pre-Nov 2023 Polymarket fills from the Hugging Face bulk set (DuckDB remote query), if older seasons are needed.

- [ ] (Nov 5, 2026) DraftKings direct feed (CT) every 30-60 s from Jeffrey's home connection: run live_capture/Probe_DraftKings.bat, then build the poller + switch alert source (cloud/GitHub is 403)
- [x] (Nov 5, 2026; done Nov 6 3:37 AM ET) Scrub Kalshi test files (sharp/data/kalshi) from this repo's git history; Jeffrey approved, scheduled Nov 6 3:30 AM ET (pause pushing workflows, filter-repo, force-push, re-enable).

- [ ] Always-on machine (Raspberry Pi or ~$5/mo cloud server) for alerts seconds after a line posts; Jeffrey looking into hardware (Nov 5, 2026; betting-goals GOALS.md + FINDINGS.md)

- [ ] Odds feed (Nov 5): analyse research/feed/ once a week of data exists: first-seen latency, CLV on quarters/halves/alt lines/props, DK vs FD stale prices, repo size check. Add NHL/NFL alert code switch to direct DK lines. Find a FanDuel page id for college hockey. Tap-test DK slip links.

## Line already moved toward the model (Nov 6, 2026; analysis/fast_move_units.py)
- [x] [LEAD] (TESTED Nov 6: REJECTED, see betting-goals models/tests/MOVE_CAP_RESULTS.md; moved-3+ bets went 76 bets 59.2% +10.3u on NBA spreads + NFL spreads/totals, better than moves of 0.5-2.5 at 49.4% -46.1u; no cap) Totals bets placed AFTER the DK line moved 3+ toward the model (3+ still left) were break-even in 2023-26 (242 bets, 51.7%, -2.9u), vs +5.1/100 for moves of 0.5-2.5. Test capping the "moved toward with 3+ left" BET rule at moves under 3 pts: pre-register, then check on spreads 2023-26 and the NFL snapshots (different market/sport = not chosen there).
- [x] [LEAD] (TESTED Nov 6: REJECTED, betting-goals models/tests/NBA_SPREAD_MOVED_TOWARD_RESULTS.md: with the live number and live filters, moved-toward spread bets went 69 bets 59.4% +9.2u; the -31.5u came from leaving out the live filters. Correction: the number was the 8 PM-report Model 1, not opener-time) (exploratory, from the move-cap test) With the OPENER-time model number, spread bets taken after a SMALL move toward the model (0.5-2.5, 3+ left) lost: NBA spreads 2023-26 431 bets 48.3% -31.5u, NFL spreads 2020-25 203 bets 46.8% -20.7u (NFL totals +6.1u). Not pre-registered. Follow-up: does it hold with the live spread number (NBA after the 8 PM report), and is it just the line moving to the close? Pre-register a check of the live spread verdict's 'moved toward' branch vs 'at the opener' on 2023-26.
- [x] [IDEA] (TESTED Nov 6: CONFIRMED at SBR openers 2013-14..2021-22, betting-goals models/tests/NBA_SPREAD_FILTERS_SBR_RESULTS.md: kept 955 bets 53.5% +20.5u vs removed 1,005 bets 46.1% -121.1u, 8 of 9 seasons; the Feb-Apr traps carry it, the Oct-Jan home-dog filter is weak at openers) (Nov 6, spread moved-toward test) Without the live filters (Oct-Jan no home dogs; Feb-Apr traps) moved-toward spread bets lost ~-23 to -29u in 2023-26, with them +16u. Check when and on which seasons those filters were chosen; if chosen on 2023-26, test them on SBR 2012-22 openers/closes (home-dog and trap flags need standings only).
- [x] [LEAD] (TESTED Nov 6: INCONCLUSIVE, betting-goals models/tests/NBA_HOMEDOG_INJURY_ABLATION_RESULTS.md: without injury features home dogs -10.4/100 vs -15.8/100 with; the 333 home-dog bets both versions make lost -52.4u, so injuries are at most a small part) (Nov 6, SBR filter test, not pre-registered) The Oct-Jan home-underdog filter barely separates at openers on 2013-22 (home dogs 51.2% -7.5u vs rest 53.8% +15.1u); on 2023-26 it was -58.6u. Check whether the 2023-26 home-dog loss is the injury features (the old model has none) before relying on it.
- [ ] [LEAD] (Nov 6, arrival trap on SBR openers 2013-22, pre-registered: REJECTED) Feb-Apr bets on teams with a recent arrival went 67 bets 58.2% +7.5u vs 55.7% without: the third live trap removed winners on older seasons (it lost every season on 2023-26, where it was chosen). Jeffrey to decide: keep it, or drop it and paper-track. Re-check on 2023-26 with the live number after the season.
- [ ] [IDEA] (Nov 6, ablation, not pre-registered) Oct-Jan home dogs without injury features: 194 bets +0.7u vs 165 bets -14.2u with. If the home-dog loss in Oct-Jan is partly injury-driven, try a home-side injury weight; pre-register on 2023-26 LOSO first.
- [ ] [IDEA] Moves of 3+ within the first hour were too rare in the hourly-ish Odds API history (7 games) to judge on their own. The minute-level DK direct feed (state/line_history.csv) will build that sample; it is a running check, not the test (RULE 2: past seasons already say the moved line is not worth more units).
- [ ] [IDEA] If a move toward us is predictable (movement model v1-an), size up AT THE OPENER when the movement model also expects a move toward the model; the same games won 61.3% at the opener. Test on 2024-26 with the walk-forward movement model predictions.
- [ ] (Nov 6, 2026) Polymarket follow test, final: download NBA + NCAAM test periods (needs Actions minutes in the private repo), re-run grader unchanged. Then a NEW pre-registration (not a re-grade): exclude market-maker wallets (both-sided, short hold), rank on profit-at-close / CLV vs the line at their FIRST fill, follower enters at the next fill after the wallet's first fill.
- [x] [FIXED Nov 6 2026: bet_record.py matches the sport (NBA team codes -> NBA versions only)] [LEAD] (Nov 6, 2026, bet recaps) NBA alerts.csv / picks_log.csv had no scores for Nov 4-5 games at 11 AM Nov 6 (Kaggle results lag). Add ESPN's scoreboard as a fallback in tracker.py grade_alerts (betting-goals ops/recap.py already grades from it, marked *). Also fix bet_record.py: NBA spreads logged after Nov 5 11:30 get the "NCAAM spreads v1" tag (same market name "spread").
- [ ] [NEXT, Nov 6 2026] Fanatics (Jeffrey's third CT book): feed live (fanatics_feed.py, Action Network book 2821, all sports). Next: (1) add Fanatics to every alert's best-book comparison (fanduel.compare in nba/nhl/nfl), (2) Fanatics props from BettingPros (book 14) for NBA/NFL props, (3) grade each live model at Fanatics openers once a few weeks of lines exist.
