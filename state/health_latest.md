# NBA pipeline health, 2026-11-06 15:30 UTC

Status: **PROBLEMS**

```
OK    Line check + alerts: last run 0.1 h ago
OK    Morning run: last run 22.8 h ago
BAD   Evening run (evening.yml): last run failure 12.1 h ago
OK    Early model run (2-4 days ahead): last run 1.7 h ago
OK    Live line recorder: last run 7.5 h ago
OK    Sharp money tracker (about every minute): last run 0.9 h ago
OK    Pipeline watchdog (every 10 min; pushes when anything breaks): last run 0.3 h ago
OK    Props loop (FanDuel lines + prop alerts every ~2 min): last run 0.0 h ago
OK    Economics (GDP) recorder: last run 2.3 h ago
OK    NCAAM daily (test-only): last run 0.4 h ago
OK    Kaggle tables archive (data-source audit, Nov 5 2026): last run 1.0 h ago
OK    Props shadow (FanDuel hourly): last run 1.1 h ago
OK    alert run 42235943064: 10 checks, 0 failed
OK    alert run 42228465975: 10 checks, 0 failed
OK    alert run 42218596893: 11 checks, 0 failed
OK    Alert log: 1.6 h old
OK    DraftKings line history: 0.2 h old
OK    Polymarket prices: -0.0 h old
OK    Pre-game lines every minute (all books, all periods): -0.0 h old
OK    Bluesky reporter posts: 0.3 h old
OK    DraftKings odds snapshots: 0.1 h old
OK    Book odds snapshots: -0.0 h old
OK    ESPN news log: 13.8 h old
OK    ESPN predictor log: 0.7 h old
OK    Edge statistics (daily): 22.8 h old
OK    Betting splits: 0.1 h old
BAD   Bet record (daily grading) (state/bet_record.csv): newest data 49.0 h old (limit 30 h)
OK    Picks log: 22.8 h old
BAD   Record by model version (state/record_by_version.csv): newest data 49.0 h old (limit 30 h)
OK    Provisional bets review (daily; stop lines in research/PROVISIONAL_BETS.md): 22.8 h old
OK    Last morning/evening run marker: 22.8 h old
OK    Line jumps log: 3.6 h old
OK    Market moves log: 60.1 h old
OK    Polymarket paper trades: 1.4 h old
OK    Sharp money live captures: 0.0 h old
OK    NCAAM scores and lines: 0.4 h old
OK    NCAAM test record (daily): 0.4 h old
OK    NCAAM M2 totals test record (daily): 0.4 h old
OK    NCAAM live ratings (daily): 0.4 h old
OK    NCAAM DraftKings first-seen lines (alert loop): -0.0 h old
OK    NCAAM PROVISIONAL record (daily): 0.4 h old
OK    Shadow record of bets passed for a line move against (daily): 22.8 h old
OK    FanDuel player props (hourly): 0.0 h old
OK    Props shadow record (paper, daily): 5.9 h old
OK    Player box stats 2026-27 (daily): 5.9 h old
OK    Kaggle tables archive (box scores, schedule): 1.0 h old
WARN  Bet timing log (state/bet_timing.csv): newest data 60.1 h old (limit 30 h)
OK    Official injury reports: 22.8 h old
OK    Injury decision log: 37.7 h old
OK    Live line recorder: 9.9 h old
OK    Live odds: 28.3 h old
OK    Model output archive: -0.0 h old
OK    Player props: 0.0 h old
OK    Period scores: -0.0 h old
OK    Timeline: -0.0 h old
OK    Media log: 136.6 h old
OK    Check log: -0.0 h old
OK    Picks log by model: 22.8 h old
OK    Shrunk picks log: 22.8 h old
OK    Stack picks log: 22.8 h old
OK    Shooting luck: 22.8 h old
OK    Shots 2026-27: 22.8 h old
OK    Early model files: 1.7 h old
OK    Pinnacle now: 28.3 h old
OK    Injury status seen: 0.2 h old
OK    Report watcher log (TEST, Nov 4 2026): 0.2 h old
OK    Report watcher grades (daily): 22.8 h old
OK    Report watcher memory: -0.0 h old
OK    Altitude tripwire watch: 22.8 h old
OK    Market models predictions (PROVISIONAL movement bets, Nov 5 2026): -0.0 h old
OK    Market models opener model refit: 0.6 h old
OK    Market models DK first lines (Action Network): 9.8 h old
OK    Box scores 2026-27 (market models): 5.9 h old
WARN  UNREGISTERED data path research/PROVISIONAL_CANDIDATES_2026-11-05.md: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path research/dk_direct: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path research/feed: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path research/stats_catalog: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/bailout_alerts.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/dk_direct_last.json: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/dk_direct_now.json: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/heartbeat_alert.txt: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/pinnacle_off: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/props_daily_done.txt: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/props_fd_runs.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/props_live.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/shadow_passed.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/watchdog.json: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/watchdog_log.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED scheduled workflow odds-feed.yml: add it to WORKFLOWS in health_check.py
OK    Morning run: no step failures in last run log
OK    Evening run: no step failures in last run log
OK    Early model run (2-4 days ahead): no step failures in last run log
OK    Live line recorder: no step failures in last run log
OK    Sharp money tracker (about every minute): no step failures in last run log
OK    Pipeline watchdog (every 10 min; pushes when anything breaks): no step failures in last run log
OK    Props loop (FanDuel lines + prop alerts every ~2 min): no step failures in last run log
OK    Economics (GDP) recorder: no step failures in last run log
OK    NCAAM daily (test-only): no step failures in last run log
OK    Kaggle tables archive (data-source audit, Nov 5 2026): no step failures in last run log
OK    Props shadow (FanDuel hourly): no step failures in last run log
OK    last successful alert.py call 0.0 h ago
OK    20 'Alerts' commits in the last 6 h
OK    provisional bets: no stop/promote line crossed
```
