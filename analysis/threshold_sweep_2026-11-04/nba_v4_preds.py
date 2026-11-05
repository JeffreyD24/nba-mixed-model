# Run from the repo root: python analysis/threshold_sweep_2026-11-04/nba_v4_preds.py . (writes nba_v4_preds.csv here, then run nba_sweep.py and nba_shop.py from this folder)
# Build live-v4 NBA totals predictions at DraftKings openers, 2023-24..2025-26, all games (luck 5+ games, form 10+ games)
import os, sys, io, contextlib
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."; sys.path.insert(0, W); os.chdir(W)
src = open("nba_mixed_model.py").read()
ns = {"__name__": "nm_lag"}
exec(compile(src.replace("past = L_all[L_all.date < d]", "past = L_all[L_all.date < d - pd.Timedelta(days=LAG_DAYS)]"), "nm_lag", "exec"), ns)
ns["LAG_DAYS"] = 1
T = pd.read_csv("data/training_games.csv")
O = pd.read_csv("data/odds_history/nba_open_close.csv")
dk = O[O.book == "draftkings"][["date", "home", "away", "open_spread", "open_total", "close_total"]].drop_duplicates(["date", "home", "away"])
T = T.drop(columns=["open_spread", "open_total"]).merge(dk, on=["date", "home", "away"], how="left")
R = []
for test in (2024, 2025, 2026):
    train = list(range(2022, test))
    with contextlib.redirect_stdout(io.StringIO()):
        _, P = ns["run"](T[T.season.isin(train + [test])], train, test, today_suffix="_open")
    R.append(P.assign(season=test)); print("Model 1", test, len(P), flush=True)
P = pd.concat(R, ignore_index=True).dropna(subset=["open_total", "close_total", "home_pts"]); P["date"] = pd.to_datetime(P.date)
TT = T.copy(); TT["date"] = pd.to_datetime(TT.date); TT = TT[TT.home_pts.notna()]
tp = pd.concat([TT[["season","date","home"]].rename(columns={"home":"team"}).assign(tp=TT.home_pts+TT.away_pts),
                TT[["season","date","away"]].rename(columns={"away":"team"}).assign(tp=TT.home_pts+TT.away_pts)]).sort_values("date")
H = {k: g for k, g in tp.groupby(["season","team"])}
TG = pd.read_csv("analysis/shot_quality_team_games.csv.gz"); TG["date"] = pd.to_datetime(TG.date)
HL = {k: g.sort_values("date") for k, g in TG.groupby(["season","team"])}
def f(season, team, d):
    g = H.get((season, team)); g = g[g.date < d - pd.Timedelta(days=1)] if g is not None else None
    n = 0 if g is None else len(g)
    if not n: return 0, np.nan, np.nan
    l = HL.get((season, team)); l = l[l.date < d - pd.Timedelta(days=1)] if l is not None else None
    luck = (l.luck.mean() + l.opp_luck.mean()) if l is not None and len(l) >= 5 else np.nan
    return n, g.tp.tail(10).mean() - g.tp.mean(), luck
for side in ("home","away"):
    F = [f(s,t,d) for s,t,d in zip(P.season, P[side], P.date)]
    for i, c in enumerate(("n","f10","luck")): P[f"{side}_{c}"] = [x[i] for x in F]
P["L"] = P.home_luck + P.away_luck; ok = P.L.notna()
P["Lc"] = P.L - P[ok].groupby("date").L.transform("mean"); P["Lc"] = P.Lc.fillna(0.0)
ng = np.minimum(P.home_n, P.away_n)
form = np.where(ng >= 10, (P.home_f10 + P.away_f10).fillna(0), 0.0)
P["v4"] = P.pred_total - 0.5*P.Lc*ng/(ng+15) + 0.20*form + 3.8*P.home.isin(["den","utah"])
P["min_games"] = ng
P[["season","date","home","away","home_pts","away_pts","open_total","close_total","pred_total","v4","min_games"]].to_csv(
    "analysis/threshold_sweep_2026-11-04/nba_v4_preds.csv", index=False)
print("saved", len(P), P.groupby("season").size().to_dict())
