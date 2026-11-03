# NBA player-game history and "missed the last game" value, 2011-12 .. 2025-26 (job A)

Not yet fetched: the Claude workspace cannot reach ESPN, so `fetch_nba_box.py` runs in GitHub Actions (`.github/workflows/fetch-nba-box.yml`, manual run, saves and pushes
after each season, safe to rerun), then `build_missed_value.py` combines and checks. This README is updated with counts after the run.

- Source: ESPN public site API (`scoreboard` by date, `summary?event=` box score), the same feeds `backfill_minutes.py` uses. The spec named the NBA stats API; stats.nba.com
  blocks cloud IPs, so ESPN is used. ESPN lists players who dressed but did not play (didNotPlay); fully inactive players are simply absent from a game, which the "missed" rule treats as not playing.
- `player_games_2012_2026.csv.gz`: season (END year), date (Eastern), game_id (ESPN event id), team (repo code), home, player_id, player, minutes, played, plus_minus, starter.
- `missed_value.csv`: per (date, team): `n_missed`, `missed_minutes_pg`, `missed_value`. Reference game R = team's latest game dated at least 2 days before (the repo's one-day lag, so it is known at the opener).
  missed_value = sum over players who played for the team this season, whose latest team is this one, and who did not play in R, of (minutes per game through R)/48 x last season's rating
  (last season's RAPM where analysis/rapm_by_season.csv covers it, i.e. seasons 2023-26; otherwise last season's plus-minus per 48 shrunk by n/(n+500), n = minutes; no prior rating = 0).
  **Sign convention: positive = the missed players were good (the team is weaker).** The tournament should enter it as a feature with its own fitted sign, not assume one.
- Checks (`checks.txt`): games per team-season, team minutes near 240 + 25 per overtime, reference game at least 2 days before.
- Known limits: the previous-season rating means first-year players count as 0; trades are handled by using each player's latest team as of the cutoff; the 2020 bubble seasons have unusual game counts.
