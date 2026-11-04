"""NBA totals: live v4 vs the stack on the same games, 2024-26 (pre-registered: research/tournament/NBA_V4_VS_STACK_PREREG.md, commit 1c4c82c).
Descriptive (already-seen seasons). Needs _tmp/old_sbr_preds_{2024,2025,2026}.csv (nba_tournament.py predict) for the stack-as-tested input.
  python analysis/nba_v4_vs_stack.py WORKDIR -> analysis/nba_v4_vs_stack_output.txt"""
import os, sys, io, contextlib, json
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
TESTS = (2024, 2025, 2026)
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
rng = np.random.default_rng(1103)

# ---- Model 1 with injuries, lag 1, at DraftKings openers (as analysis/lag_leak_test.py)
src = open(os.path.join(W, "nba_mixed_model.py")).read()
ns = {"__name__": "nm_lag"}
exec(compile(src.replace("past = L_all[L_all.date < d]", "past = L_all[L_all.date < d - pd.Timedelta(days=LAG_DAYS)]"), "nm_lag", "exec"), ns)
ns["LAG_DAYS"] = 1
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"))
dk = O[O.book == "draftkings"][["date", "home", "away", "open_spread", "open_total", "close_total"]].drop_duplicates(["date", "home", "away"])
T = T.drop(columns=["open_spread", "open_total"]).merge(dk, on=["date", "home", "away"], how="left")
R = []
for test in TESTS:
    train = [s for s in range(2022, test)]
    with contextlib.redirect_stdout(io.StringIO()):
        _, P = ns["run"](T[T.season.isin(train + [test])], train, test, today_suffix="_open")
    R.append(P.assign(season=test)); print("Model 1", test, flush=True)
P = pd.concat(R, ignore_index=True).dropna(subset=["open_total", "close_total", "home_pts"])
P["date"] = pd.to_datetime(P.date)

# ---- season-to-date features through two nights before (box scores: simple, form, n, rested; shots: luck)
TT = T.copy(); TT["date"] = pd.to_datetime(TT.date); TT = TT[TT.home_pts.notna()]
tp = pd.concat([TT[["season", "date", "home"]].rename(columns={"home": "team"}).assign(tp=TT.home_pts + TT.away_pts),
                TT[["season", "date", "away"]].rename(columns={"away": "team"}).assign(tp=TT.home_pts + TT.away_pts)]).sort_values("date")
H = {k: g for k, g in tp.groupby(["season", "team"])}
TG = pd.read_csv(os.path.join(W, "analysis", "shot_quality_team_games.csv.gz")); TG["date"] = pd.to_datetime(TG.date)
HL = {k: g.sort_values("date") for k, g in TG.groupby(["season", "team"])}
sched = set(zip(pd.concat([TT.home, TT.away]), pd.concat([TT.date, TT.date])))
def f(season, team, d):
    g = H.get((season, team)); g = g[g.date < d - pd.Timedelta(days=1)] if g is not None else None
    n = 0 if g is None else len(g)
    if not n: return 0, np.nan, np.nan, np.nan
    l = HL.get((season, team)); l = l[l.date < d - pd.Timedelta(days=1)] if l is not None else None
    luck = (l.luck.mean() + l.opp_luck.mean()) if l is not None and len(l) >= 5 else np.nan
    return n, g.tp.mean(), g.tp.tail(10).mean() - g.tp.mean(), luck
for side in ("home", "away"):
    F = [f(s, t, d) for s, t, d in zip(P.season, P[side], P.date)]
    for i, c in enumerate(("n", "avg", "f10", "luck")): P[f"{side}_{c}"] = [x[i] for x in F]
P = P[(P.home_n >= 10) & (P.away_n >= 10) & P.home_luck.notna() & P.away_luck.notna() ].copy()
P["L"] = P.home_luck + P.away_luck; P["Lc"] = P.L - P.groupby("date").L.transform("mean")
P["rested"] = [float(((h, d - pd.Timedelta(days=1)) not in sched) and ((a, d - pd.Timedelta(days=1)) not in sched)) for h, a, d in zip(P.home, P.away, P.date)]
P["alt"] = P.home.isin(["den", "utah"]).astype(float)
P["simple"] = (P.home_avg + P.away_avg) / 2; P["form"] = P.home_f10 + P.away_f10
P["y"] = P.home_pts + P.away_pts - P.open_total
P["move"] = P.close_total - P.open_total
ng = np.minimum(P.home_n, P.away_n)
P["v4"] = P.pred_total - 0.5 * P.Lc * ng / (ng + 15) + 0.20 * P.form + 3.8 * P.alt
P.to_csv(os.path.join(W, "research", "stats_catalog", "nba_totals_games.csv"), index=False)
print(len(P))
