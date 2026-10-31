"""
Join the Kaggle box scores to the existing training games (2021-22 .. 2025-26).

Outputs (in work dir):
  games_v2.csv   training_games.csv + gameId, team ids, possessions and minutes per team
  team_codes.csv teamId -> code used in training_games (e.g. 1610612744 -> gs)
"""
import pandas as pd, numpy as np

W = "/home/claude/work/"
tg = pd.read_csv("/home/claude/nba-mixed-model/data/training_games.csv", parse_dates=["date"])
G = pd.read_parquet(W + "games_all.parquet")
G["date"] = pd.to_datetime(G.d.dt.date)
T = pd.read_parquet(W + "team_stats.parquet")

# ---- match games on date + both scores (then learn team-code mapping)
m = tg.merge(G[["gameId", "date", "hometeamId", "awayteamId", "homeScore", "awayScore", "gameType"]],
             left_on=["date", "home_pts", "away_pts"], right_on=["date", "homeScore", "awayScore"], how="left")
print("unmatched", m.gameId.isna().sum(), "dups", m.duplicated(["date", "home", "away"]).sum())
codes = (pd.concat([m[["hometeamId", "home"]].rename(columns={"hometeamId": "tid", "home": "code"}),
                    m[["awayteamId", "away"]].rename(columns={"awayteamId": "tid", "away": "code"})])
         .dropna().groupby("tid").code.agg(lambda s: s.mode()[0]))
codes.index = codes.index.astype(int)
assert codes.nunique() == 30 and len(codes) == 30, codes
code2tid = {c: t for t, c in codes.items()}
codes.to_csv(W + "team_codes.csv", header=["code"])

# re-match strictly on date + home + away team
tg["home_tid"] = tg.home.map(code2tid); tg["away_tid"] = tg.away.map(code2tid)
m = tg.merge(G[["gameId", "date", "hometeamId", "awayteamId", "homeScore", "awayScore"]],
             left_on=["date", "home_tid", "away_tid"], right_on=["date", "hometeamId", "awayteamId"], how="left")
bad = m.gameId.isna() | (m.homeScore != m.home_pts) | (m.awayScore != m.away_pts)
print("strict unmatched/mismatched:", int(bad.sum()))
m = m[~bad].drop(columns=["hometeamId", "awayteamId", "homeScore", "awayScore"])

# ---- possessions per team-game: FGA - OREB + TOV + 0.44 FTA
T["poss"] = T.fieldGoalsAttempted - T.reboundsOffensive + T.turnovers + 0.44 * T.freeThrowsAttempted
T = T[["gameId", "teamId", "poss", "numMinutes", "teamScore", "freeThrowsAttempted", "foulsPersonal"]]
for side in ("home", "away"):
    x = T.rename(columns={c: f"{side}_{c}" for c in T.columns if c not in ("gameId", "teamId")})
    m = m.merge(x, left_on=["gameId", f"{side}_tid"], right_on=["gameId", "teamId"], how="left").drop(columns="teamId")
print("missing possessions:", m.home_poss.isna().sum(), m.away_poss.isna().sum())
print("score check (team stats vs games):", int((m.home_teamScore != m.home_pts).sum()))
m["game_min"] = m.home_numMinutes                      # 240 regulation, +25 per OT
m["pace48"] = (m.home_poss + m.away_poss) / 2 * 240 / m.game_min
print(m.groupby("season")[["pace48", "game_min"]].mean().round(2))
m.to_csv(W + "games_v2.csv", index=False)
print("games_v2:", len(m), m.season.value_counts().sort_index().to_dict())
