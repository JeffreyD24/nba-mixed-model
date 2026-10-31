"""Coach-level rotation analysis: does a coach's 2nd-half rotation style follow him to a new team, and do back-to-back habits repeat?
python analysis/coach_rotations.py   (from the repo folder)"""
import glob, numpy as np, pandas as pd

d = pd.concat([pd.read_csv(f) for f in glob.glob("research/minutes_history/*.csv")])
d = d[(d.groupby("espn_event_id").check_max_diff_min.transform("first") <= 1) & ~d.dnp.fillna(False)]
d["bench"] = ~d.starter.astype(bool)
def agg(x):
    return pd.Series(dict(bench_h2=x.loc[x.bench, "h2"].sum() / x.h2.sum(),
                          star_q4=x.loc[~x.bench, "q4"].sum(),
                          top_h2=x.sort_values("total_min").h2.iloc[-1]))
tg = d.groupby(["season", "espn_event_id", "date", "team", "home", "away"]).apply(agg).reset_index()
tg["date"] = pd.to_datetime(tg.date); tg = tg.sort_values(["team", "date"])
tg["b2b"] = tg.groupby("team").date.diff().dt.days.eq(1)
G = pd.read_csv("data/training_games.csv", parse_dates=["date"]); G["margin"] = (G.home_pts - G.away_pts).abs()
tg = tg.merge(G[["date", "home", "away", "margin"]], on=["date", "home", "away"], how="left")
C = pd.read_csv("data/coaches.csv", parse_dates=["start"]).sort_values("start")
tg = pd.merge_asof(tg.sort_values("date"), C[["team", "start", "coach", "interim"]].rename(columns={"start": "date"}),
                   on="date", by="team", direction="backward")
close = tg[tg.margin <= 10]
M = ["bench_h2", "star_q4", "top_h2"]

# 1) style by coach-team-season (close games, 20+ games, not interim)
cs = close[~close.interim].groupby(["coach", "team", "season"]).agg(n=("bench_h2", "size"), **{m: (m, "mean") for m in M}).reset_index()
cs = cs[cs.n >= 20]
ts = close.groupby(["team", "season"])[M].mean()          # team style that season (any coach)
moves = []
for coach, x in cs.sort_values("season").groupby("coach"):
    teams = x.team.tolist()
    for i in range(1, len(x)):
        a, b = x.iloc[i - 1], x.iloc[i]
        if a.team != b.team and b.season - a.season <= 2:
            prev = ts.loc[(b.team, a.season)] if (b.team, a.season) in ts.index else None   # new team's style under its old coach
            if prev is not None:
                moves.append(dict(coach=coach, old_team=a.team, new_team=b.team, old_season=a.season, new_season=b.season,
                                  **{f"{m}_coach_before": a[m] for m in M}, **{f"{m}_team_before": prev[m] for m in M},
                                  **{f"{m}_after": b[m] for m in M}))
MV = pd.DataFrame(moves)
print(f"Coaches who changed teams (20+ close games at each): {len(MV)}")
for m in M:
    if len(MV) >= 4:
        print(f"  {m:9s} new team's style after the move: corr with coach's old style {MV[f'{m}_after'].corr(MV[f'{m}_coach_before']):+.2f}, "
              f"with the new team's old style {MV[f'{m}_after'].corr(MV[f'{m}_team_before']):+.2f}")
print(MV[["coach", "old_team", "new_team", "new_season"] + [f"bench_h2_{k}" for k in ("coach_before", "team_before", "after")]].round(3).to_string())

# 2) coach back-to-back habit, season to next season (same coach, any team)
rows = []
for (coach, season), x in close[~close.interim].groupby(["coach", "season"]):
    b, r = x[x.b2b], x[~x.b2b]
    if len(b) >= 5 and len(r) >= 15:
        rows.append(dict(coach=coach, season=season, **{m: b[m].mean() - r[m].mean() for m in M}))
B = pd.DataFrame(rows); B["next"] = B.season + 1
P = B.merge(B, left_on=["coach", "next"], right_on=["coach", "season"], suffixes=("", "_n"))
print(f"\nCoach back-to-back effect, one season vs the next (same coach, {len(P)} pairs):")
for m in M: print(f"  {m:9s} corr {P[m].corr(P[m + '_n']):+.2f}")
# 3) coach style season to season
S = close[~close.interim].groupby(["coach", "season"])[M].mean().reset_index(); S["next"] = S.season + 1
Q = S.merge(S, left_on=["coach", "next"], right_on=["coach", "season"], suffixes=("", "_n"))
print(f"\nCoach overall style, one season vs the next ({len(Q)} pairs):")
for m in M: print(f"  {m:9s} corr {Q[m].corr(Q[m + '_n']):+.2f}")
