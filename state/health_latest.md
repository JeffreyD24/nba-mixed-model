# NBA pipeline health, 2026-11-07 13:06 UTC

Status: **WARNINGS**

```
OK    Line check + alerts: last run 0.6 h ago
OK    Morning run: last run 20.6 h ago
OK    Evening run: last run 9.7 h ago
OK    Early model run (2-4 days ahead): last run 11.4 h ago
OK    Live line recorder: last run 4.8 h ago
OK    Sharp money tracker (about every minute): last run 1.1 h ago
OK    Pipeline watchdog (every 10 min; pushes when anything breaks): last run 0.8 h ago
OK    Props loop (FanDuel lines + prop alerts every ~2 min): last run 0.3 h ago
OK    Economics (GDP) recorder: last run 0.1 h ago
OK    NCAAM daily (test-only): last run 13.1 h ago
OK    Kaggle tables archive (data-source audit, Nov 5 2026): last run 13.6 h ago
OK    Props shadow (FanDuel hourly): last run 0.2 h ago
WARN  alert run 42367779348: ntfy refused 6 push attempt(s) (rate limit); retries got them through
WARN  alert run 42367779348: 1 of 10 line checks failed.
OK    alert run 42365299349: 11 checks, 0 failed
OK    alert run 42362344780: 10 checks, 0 failed
OK    Alert log: 1.4 h old
OK    DraftKings line history: 0.2 h old
OK    Polymarket prices: 0.0 h old
OK    Pre-game lines every minute (all books, all periods): 0.0 h old
OK    Bluesky reporter posts: 0.2 h old
OK    DraftKings odds snapshots: 0.2 h old
OK    Book odds snapshots: 0.0 h old
OK    ESPN news log: 8.5 h old
OK    ESPN predictor log: 0.0 h old
OK    Edge statistics (daily): 20.6 h old
OK    Betting splits: 0.0 h old
OK    Bet record (daily grading): 20.6 h old
OK    Picks log: 9.7 h old
OK    Record by model version: 20.6 h old
OK    Provisional bets review (daily; stop lines in research/PROVISIONAL_BETS.md): 20.6 h old
OK    Last morning/evening run marker: 9.7 h old
OK    Line jumps log: 5.9 h old
OK    Market moves log: 19.2 h old
OK    Polymarket paper trades: 1.5 h old
OK    Sharp money live captures: 0.1 h old
OK    NCAAM scores and lines: 22.0 h old
OK    NCAAM test record (daily): 13.1 h old
OK    NCAAM M2 totals test record (daily): 13.1 h old
OK    NCAAM live ratings (daily): 13.1 h old
OK    NCAAM DraftKings first-seen lines (alert loop): 0.0 h old
OK    NCAAM PROVISIONAL record (daily): 13.1 h old
OK    Shadow record of bets passed for a line move against (daily): 20.6 h old
OK    FanDuel player props (hourly): 0.0 h old
OK    Props shadow record (paper, daily): 1.0 h old
OK    Player box stats 2026-27 (daily): 1.0 h old
OK    Kaggle tables archive (box scores, schedule): 13.6 h old
OK    Bet timing log: 9.7 h old
OK    Official injury reports: 9.7 h old
OK    Injury decision log: 12.8 h old
OK    Live line recorder: 7.0 h old
WARN  Live odds (research/live_odds): newest data 49.9 h old (limit 30 h)
OK    Model output archive: 0.1 h old
OK    Player props: 0.0 h old
OK    Period scores: 0.0 h old
OK    Timeline: 0.0 h old
OK    Media log: 158.2 h old
OK    Check log: 0.0 h old
OK    Picks log by model: 9.7 h old
OK    Shrunk picks log: 20.6 h old
OK    Stack picks log: 20.6 h old
OK    Shooting luck: 20.6 h old
OK    Shots 2026-27: 20.6 h old
OK    Early model files: 11.4 h old
OK    Pinnacle now: 49.9 h old
OK    Injury status seen: 12.6 h old
OK    Report watcher log (TEST, Nov 4 2026): 12.6 h old
OK    Report watcher grades (daily): 20.6 h old
OK    Report watcher memory: 0.1 h old
OK    Altitude tripwire watch: 9.7 h old
OK    Market models predictions (PROVISIONAL movement bets, Nov 5 2026): 0.0 h old
OK    Market models opener model refit: 0.2 h old
OK    Market models DK first lines (Action Network): 9.7 h old
OK    Box scores 2026-27 (market models): 1.0 h old
WARN  UNREGISTERED data path research/PROVISIONAL_CANDIDATES_2026-11-05.md: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path research/dk_direct: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path research/feed: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path research/stats_catalog: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/alert_audit_latest.md: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/alert_audit_log.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/bailout_alerts.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/dk_direct_last.json: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/dk_direct_now.json: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/fanatics_shadow.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/fanatics_shadow_props.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/heartbeat_alert.txt: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/pinnacle_off: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/props_daily_done.txt: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/props_fd_runs.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/props_live.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/props_stop_sent.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/shadow_passed.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/watchdog.json: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED data path state/watchdog_log.csv: add it to STREAMS (or IGNORE) in health_check.py
WARN  UNREGISTERED scheduled workflow alert-audit.yml: add it to WORKFLOWS in health_check.py
WARN  UNREGISTERED scheduled workflow feed-archive.yml: add it to WORKFLOWS in health_check.py
WARN  UNREGISTERED scheduled workflow nba-player-movement.yml: add it to WORKFLOWS in health_check.py
WARN  UNREGISTERED scheduled workflow odds-feed.yml: add it to WORKFLOWS in health_check.py
WARN  UNREGISTERED scheduled workflow recap.yml: add it to WORKFLOWS in health_check.py
WARN  Morning run (run 42252189897): Traceback (most recent call last):; Edge statistics not updated; they will run again tomorrow.
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
OK    19 'Alerts' commits in the last 6 h
OK    provisional bets: no stop/promote line crossed
```
