"""Job A part 2: combine parts/ into player_games_2012_2026.csv.gz, run the checks, build missed_value.csv.
  python build_missed_value.py   (from this folder; needs the parts/ files and ../../../analysis/rapm_by_season.csv)
missed_value, per (date, team): sum over players who played for the team this season, whose latest team is this team, and who did NOT play in the
team's reference game R, of (their minutes per game this season through R) / 48 x their rating from LAST season.
R = the team's latest game dated <= (game date - 2 days): results through two nights before, the repo's one-day lag, so it is known at the opener.
Rating: last season's RAPM (analysis/rapm_by_season.csv, 2022-2026 seasons) when the prior season is covered, else last season's plus/minus per 48
shrunk by n/(n+500), n = minutes. No prior-season rating -> 0 (rookies, the first season)."""
import glob, os, numpy as np, pandas as pd
P = pd.concat([pd.read_csv(p, dtype={"game_id": str, "player_id": str}) for p in sorted(glob.glob("parts/season_*.csv"))], ignore_index=True)
P = P.drop_duplicates(["game_id", "player_id", "team"])
# drop All-Star / Rising Stars / exhibition pseudo-teams (east, west, leb, world, ...): real teams have 20+ games in the table
_n = P.groupby("team").game_id.nunique(); P = P[P.team.isin(_n[_n >= 20].index)]
# ESPN can list the same team twice on one date (duplicate/postponed event): keep the game with the most minutes, drop the other game entirely
_g = P.groupby(["team", "date", "game_id"]).minutes.sum().reset_index().sort_values("minutes", ascending=False)
_drop = set(_g[_g.duplicated(["team", "date"], keep="first")].game_id); P = P[~P.game_id.isin(_drop)]
# ESPN returns zero minutes / no stats for every Chicago and New Orleans game 2013-2018 (both sides of those games); empty box scores must not count
# as "everyone missed", so drop any game whose team minutes sum to < 100 and report how many (see checks.txt; diagnose_empty.py shows the raw response)
_tm = P.groupby(["game_id", "team"]).minutes.sum(); _empty = set(_tm[_tm < 100].reset_index().game_id); EMPTY_DROPPED = P[P.game_id.isin(_empty)].groupby("season").game_id.nunique().to_dict()
P = P[~P.game_id.isin(_empty)]
P["plus_minus"] = pd.to_numeric(P.plus_minus.astype(str).str.replace("+", "", regex=False), errors="coerce")
P[["season", "date", "game_id", "team", "player_id", "player", "minutes", "played", "plus_minus", "starter", "home"]].to_csv("player_games_2012_2026.csv.gz", index=False)
# ---- checks
T = P.groupby(["season", "team", "game_id"]).agg(min=("minutes", "sum")).reset_index()
n = T.groupby(["season", "team"]).size().unstack(0)
L = [f"player-game rows {len(P)} (after dropping All-Star teams, duplicate events and empty box scores)", f"empty box-score games dropped by season: {EMPTY_DROPPED}", "games per team-season (min/max by season; expect 82, 66 in 2012, ~72 in 2020-21, 64-75 in 2020): "]
for s, c in n.items(): L.append(f"  {s}: {int(c.min())}-{int(c.max())} games, {c.notna().sum()} teams")
ot = ((T["min"] - 240) / 25).round(); L.append("team minutes within 3 of 240 + 25 x overtimes: %.1f%%" % (100 * ((T["min"] - 240 - 25 * ot).abs() <= 3).mean()))
L.append("median team minutes %.0f; share below 235: %.2f%%" % (T["min"].median(), 100 * (T["min"] < 235).mean()))
# ---- missed value
games = P.groupby(["season", "team", "game_id"]).date.first().reset_index(); games["date"] = pd.to_datetime(games.date)
pg = P[P.played == 1].copy(); pg["date"] = pd.to_datetime(pg.date)
prior = {}
if os.path.exists("../../../analysis/rapm_by_season.csv"):
    R = pd.read_csv("../../../analysis/rapm_by_season.csv", dtype={"athlete_id": str}); prior_rapm = {(int(r.season), r.athlete_id): r.rapm for r in R.itertuples()}
else: prior_rapm = {}
S = pg.groupby(["season", "player_id"]).agg(m=("minutes", "sum"), pm=("plus_minus", "sum")).reset_index()
rating = {}
for r in S.itertuples():
    k = (r.season + 1, r.player_id)
    rating[k] = prior_rapm[(r.season, r.player_id)] if (r.season, r.player_id) in prior_rapm else (r.pm / r.m * 48 * r.m / (r.m + 500) if r.m > 0 else 0.0)
out = []
for season, SP in pg.groupby("season"):
    SP = SP.sort_values("date")
    for team, G in games[games.season == season].groupby("team"):
        G = G.sort_values("date")
        for g in G.itertuples():
            cut = g.date - pd.Timedelta(days=2)
            prev = G[G.date <= cut]
            if prev.empty: continue
            ref = prev.iloc[-1].game_id
            hist = SP[SP.date <= cut]
            last_team = hist.sort_values("date").groupby("player_id").team.last()
            mine = last_team[last_team == team].index
            h = hist[hist.player_id.isin(mine) & (hist.team == team)]
            gp_team = len(prev)
            mpg = h.groupby("player_id").minutes.sum() / gp_team
            played_ref = set(h[h.game_id == ref].player_id)
            miss = [p for p in mpg.index if p not in played_ref]
            val = sum(mpg[p] / 48 * rating.get((season, p), 0.0) for p in miss)
            out.append(dict(season=season, date=g.date.strftime("%Y-%m-%d"), team=team, game_id=g.game_id, ref_game_date=prev.iloc[-1].date.strftime("%Y-%m-%d"),
                            n_missed=len(miss), missed_minutes_pg=float(sum(mpg[p] for p in miss)), missed_value=val))
MV = pd.DataFrame(out); MV.to_csv("missed_value.csv", index=False)
L += [f"missed_value rows {len(MV)}; mean n_missed {MV.n_missed.mean():.2f}; share with any missed {100 * (MV.n_missed > 0).mean():.0f}%",
      "missed_value mean/sd by season: " + str(MV.groupby("season").missed_value.agg(["mean", "std"]).round(2).to_dict("index")),
      "reference game is always >= 2 days before the game: %s" % bool(((pd.to_datetime(MV.date) - pd.to_datetime(MV.ref_game_date)).dt.days >= 2).all())]
open("checks.txt", "w").write("\n".join(L) + "\n"); print("\n".join(L))
