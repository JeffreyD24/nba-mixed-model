"""NCAAM live ratings for the PROVISIONAL stale-line spreads rule (Nov 5, 2026; ncaab/research/MODEL3_RESULTS_2026-11-05.md).
Runs each morning after ncaab/m2_daily.py refreshes ncaab/data/all_games.csv. Final ratings use games through TWO days ago
(the fit for the last day excludes that day) and the market model is lagged one more day (Fable review: openers can post the night before).
  python ncaab/live_ratings.py WORKDIR -> ncaab/state/live_ratings.json"""
import os, sys, json
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
src = open(os.path.join(W, "ncaab", "model3.py")).read().split("out = G.copy()")[0]
src = src.replace("past = np.where((dates < d) & S[TGT[2]].values)[0]", "past = np.where((dates < d - np.timedelta64(LAG, 'D')) & S[TGT[2]].values)[0]")
ns = {"__name__": "lr"}; sys.argv = ["x", W]; exec(src, ns); inner = ns["ns"]; G = ns["G"]
today = pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None)
G = G[G.date < today].reset_index(drop=True)                 # played games only (last day = yesterday, excluded by the fit)
inner["G"] = G
def final(tgt, lag, **kw):
    inner["TGT"] = tgt; inner["LAG"] = lag; prior = {}; seasons = sorted(G.season.unique())
    for s in seasons:
        S = G[G.season == s].reset_index(drop=True)
        pc = {k: (v * 0.8 if isinstance(k, tuple) else v) for k, v in prior.items()}
        _, _, prior = inner["run_season"](S, pc, **kw)
    out = dict(hca=float(prior["hca"]), o={}, d={}, co={}, cd={})
    for k, v in prior.items():
        if isinstance(k, tuple): out[{"o": "o", "d": "d", "co": "co", "cd": "cd"}[k[0]]][str(k[1])] = float(v)
    return out
R = dict(made_at=str(pd.Timestamp.now(tz="America/New_York"))[:16], played_through=str((today - pd.Timedelta(days=1)).date()), models={})
R["models"]["M2"] = final(("home_pts", "away_pts", "fit_all"), 0, level_half=14)
R["models"]["M8"] = final(("home_pts", "away_pts", "fit_all"), 0, ridge=10.0, cridge=10.0)
R["models"]["MKTL"] = final(("imp_h", "imp_a", "fit_mkt"), 1, ridge=0.2)
cur = G.season.max(); C = G[G.season == cur]
R["games"] = pd.concat([C.hk, C.ak]).value_counts().astype(int).to_dict()
R["conf"] = {**dict(zip(C.hk, C.home_conf_id.fillna(-1).astype(int).astype(str))), **dict(zip(C.ak, C.away_conf_id.fillna(-1).astype(int).astype(str)))}
R["blend_c"] = json.load(open(os.path.join(W, "ncaab", "data", "live_blendc.json")))["coef"]
os.makedirs(os.path.join(W, "ncaab", "state"), exist_ok=True)
json.dump(R, open(os.path.join(W, "ncaab", "state", "live_ratings.json"), "w"))
print(f"live ratings: season {cur}, {len(R['games'])} teams, played through {R['played_through']}")
