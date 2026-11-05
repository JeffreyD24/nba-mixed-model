# Props probe — 2026-11-05 09:23 UTC

## The Odds API
- credits left: 196805, used: 4803195
- historical events at 2024-01-15T22:00:00Z: HTTP 200, 12 events, cost 1
  - one game (New Orleans Pelicans @ Dallas Mavericks, tip 2024-01-15T19:41:57Z): HTTP 200, cost 40, snapshot 2024-01-15T21:55:38Z, prev 2024-01-15T21:50:38Z
  - outcomes per book/market: {"draftkings": {"player_assists": 2, "player_points": 2, "player_rebounds": 2, "player_threes": 2}, "fanduel": {"player_rebounds": 2}, "williamhill_us": {"player_points": 2, "player_rebounds": 2, "player_threes": 4}, "pinnacle": {"player_assists": 10, "player_points": 22, "player_rebounds": 10, "player_threes": 22}}
  - example: [{"name": "Over", "description": "CJ McCollum", "price": 175, "point": 4.5}, {"name": "Under", "description": "CJ McCollum", "price": -235, "point": 4.5}]
- credits left after probe: 196764

## Action Network past props
- v1/leagues/4/props/core_bet_type_27_points: HTTP 404; 0 'player' in first 300 chars; '{"statusCode":404,"error":"Not Found","message":"No Content found"}'
- v2/scoreboard/nba/props: HTTP 400; 0 'player' in first 300 chars; '{"message":"Invalid data submitted as payload","statusCode":400,"error":"Bad Request","errorCode":"INVALID_DATA"}'
- v1/scoreboard/nba: HTTP 400; 0 'player' in first 300 chars; '{"message":"Invalid data submitted as payload","statusCode":400,"error":"Bad Request","errorCode":"INVALID_DATA"}'

## ESPN past box score
- HTTP 200; stat names: ['MIN', 'PTS', 'FG', '3PT', 'FT', 'REB', 'AST', 'TO', 'STL', 'BLK', 'OREB', 'DREB', 'PF', '+/-']; first player: Chet Holmgren ['35', '17', '8-15', '0-4', '1-2', '6', '3', '1', '1', '1', '3', '3', '3', '-3']
