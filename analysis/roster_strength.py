"""Roster strength vs what the team has played with so far (no lookahead), to catch trades, buyouts and returns the
team-rating model hasn't caught up with. For each team before each game:
  rotation = players whose latest appearance (before today) was for this team, within 30 days, 3+ games and 12+ min/game for it
  value    = sum of (min per game / 48) x prior-season EPM (unrated players -1.5), scaled to 240 minutes
  delta    = value now minus the average value over this team's earlier games this season
  python analysis/roster_strength.py WORKDIR -> analysis/roster_strength.csv (date, team, value, delta, games)"""
import os, sys, re, unicodedata
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
PG = pd.read_csv("/home/claude/data/espn_player_games_2023_2026.csv", low_memory=False)
PG = PG[PG.season_type.astype(str).str.contains("Regular")].copy()
PG["minutes"] = pd.to_numeric(PG.minutes, errors="coerce"); PG = PG[PG.minutes > 0]
codes = {"GS": "gs", "NO": "no", "NY": "ny", "SA": "sa", "UTAH": "utah", "WSH": "wsh", "PHX": "phx", "BKN": "bkn"}
PG["team"] = PG.team.map(lambda t: codes.get(t, str(t).lower())); PG["date"] = pd.to_datetime(PG.game_date)
E = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/external/kaggle/deocheng_epm/public.player_epm.csv.gz"), usecols=["player_name", "season", "game_dt", "epm_tot", "epm_off", "epm_def"])
E = E.sort_values("game_dt").groupby(["player_name", "season"]).tail(1)
def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s); return re.sub(r"[^a-z]", "", s)
E["k"] = E.player_name.map(norm); PG["k"] = PG.player.map(norm)
for col, nm in (("epm_tot", "epm_prev"), ("epm_off", "off_prev"), ("epm_def", "def_prev")):
    EPM = {(k, s): v for k, s, v in zip(E.k, E.season, E[col])}
    PG[nm] = [EPM.get((k, s - 1), EPM.get((k, s - 2), np.nan)) for k, s in zip(PG.k, PG.season)]
print("player-games with a prior EPM:", PG.epm_prev.notna().mean().round(3))
PG["epm_prev"] = PG.epm_prev.fillna(-1.5); PG["off_prev"] = PG.off_prev.fillna(-1.0); PG["def_prev"] = PG.def_prev.fillna(-0.5)
out = []
for s, S in PG.groupby("season"):
    S = S.sort_values("date"); dates = sorted(S.date.unique())
    for d in dates:
        past = S[(S.date < d) & (S.date >= d - pd.Timedelta(days=60))]
        if not len(past): continue
        last = past.sort_values("date").groupby("espn_player_id").tail(1)
        last = last[last.date >= d - pd.Timedelta(days=30)]
        today_teams = set(S[S.date == d].team)
        for t in today_teams:
            ids = last[last.team == t].espn_player_id
            g = past[(past.team == t) & past.espn_player_id.isin(ids)].groupby("espn_player_id").agg(gp=("minutes", "size"), mpg=("minutes", "mean"), epm=("epm_prev", "first"), off=("off_prev", "first"), dfn=("def_prev", "first"))
            g = g[(g.gp >= 3) & (g.mpg >= 12)]
            if not len(g): continue
            share = g.mpg / g.mpg.sum() * 5          # five players on the floor
            out.append(dict(season=s, date=str(pd.Timestamp(d).date()), team=t, value=float((share * g.epm).sum()), v_off=float((share * g.off).sum()), v_def=float((share * g.dfn).sum()), n_rot=len(g)))
R = pd.DataFrame(out).sort_values(["season", "team", "date"])
g = R.groupby(["season", "team"])
R["avg_before"] = g.value.transform(lambda v: v.shift().expanding().mean()); R["games"] = g.cumcount()
R["delta"] = R.value - R.avg_before
for c in ("v_off", "v_def"): R[c + "_delta"] = R[c] - g[c].transform(lambda v: v.shift().expanding().mean())
R.to_csv(os.path.join(W, "analysis", "roster_strength.csv"), index=False)
print(R.groupby("season").delta.describe().round(2))
