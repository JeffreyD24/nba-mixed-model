# Data jobs for the tournaments (written by Opus, Nov 3, 2026). Mechanical: follow exactly, no modelling choices.

Rules for every job: public/free sources only; fetch from **GitHub Actions** (the Claude workspace can't reach these sites); store
derived tables in the repo, raw dumps git-ignored; add a row to data/external/INDEX.md and MANIFEST.csv; write a README with source,
date range, row counts and the checks below. Every row must carry the date/time the information was known.
Commit lines: Co-Authored-By + Claude-Session as the harness gives; `git pull --rebase origin main` before pushing.

## Job A: NBA "missed the last game" history, 2011-12 .. 2025-26 (nba-mixed-model)
- Source: NBA stats API box scores (`leaguegamelog` / `boxscoretraditionalv2`, as in backfill_minutes.py), one row per player-game
  including DNPs, minutes, team, date.
- Output `data/external/nba_box/player_games_2012_2026.csv.gz`: season (END year), date, game_id, team, player_id, minutes, played (0/1).
- Checks: games per team-season = 82 (66 in 2011-12, 64-77 in 2019-20, 72 in 2020-21); team minutes per game 240 (265 per OT).
- Then a feature table `data/external/nba_box/missed_value.csv`: for each game and team, sum over players who did NOT play in the team's
  previous game of (minutes per game so far this season / 48) x last season's rating. Ratings: use `analysis/rapm_by_season.csv` if it
  covers the season, else last season's +/- per 48 shrunk (n/(n+500)). Known at the opener: yes (previous game finished the night before
  at the latest; use the game before that if it was the night before, to respect the one-day lag).

## Job B: NHL starting goalies and missed regulars, 2011-12 .. 2022-23 (nhl-mixed-model)
- Source: NHL public API (`api-web.nhle.com/v1/gamecenter/{id}/boxscore`) for every regular-season game in
  data/external/hockeyr/team_game_xg_2010_2023.csv.gz (game_id is the NHL id).
- Output `data/external/nhl_box/goalies_2011_2023.csv`: game_id, date, team, starting goalie id, his shots against, goals against, TOI.
  `skaters_2011_2023.csv.gz`: game_id, team, player id, TOI.
- Checks: one starter per team-game; join rate to the hockeyR table 99%+.

## Job C: NFL injury and practice reports, 2011-2021 (nfl-mixed-model)
- Source: nflverse `injuries` releases (nflreadr::load_injuries, 2009+), files on GitHub releases (reachable from the workspace too).
- Output `data/external/nflverse_injuries/injuries_2011_2021.csv.gz` as published, plus season/week/team/player/report_status/
  practice_status/date_modified. Checks: every week has 32 teams (31/30 earlier where relevant).

## Job D: archived weather forecasts for NFL games, 2022-2025 (nfl-mixed-model)
- Source: Open-Meteo Historical Forecast API (archive of past model runs). For each outdoor game, the forecast for kickoff hour as it
  stood 6 days and 1 day before kickoff: wind mph, temp F, precipitation.
- Output `data/external/weather_forecasts/nfl_forecasts_2022_2025.csv`. Check: forecast made_at is before the opener time.

When a job is done, stop: Opus writes the next tournament spec that uses it.
