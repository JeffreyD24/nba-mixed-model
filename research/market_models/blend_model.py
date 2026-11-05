"""Market models step 4: blend of v4 + DK now + expected move (STEP4_BLEND_PREREG.md, committed c0f08c4 before fitting).
Run from repo root: python research/market_models/blend_model.py
"""
import json, sys
import numpy as np, pandas as pd

# reuse step 3's panel building (Action Network books, walk-forward opener predictions) from the export script
sys.argv = [sys.argv[0], "--an", "--reach"]   # --reach: only snapshots the live code can price (Fable check, Nov 5)
src = open("research/market_models/export_movement_model.py").read().split("# ---- 1) reproduce")[0]
ns = {"__name__": "blend"}
exec(src, ns)
P, C, fit, am_units = ns["P"], ns["C"], ns["fit"], ns["am_units"]
FEAT = C.MOVE_FEAT_AN
OUT = "research/market_models/"
BE = 1.07

# expected move, season by season, from models fit on earlier seasons only
P["exp_move"] = np.nan
for s in (2024, 2025, 2026):
    m, med = fit(P[(P.season >= 2023) & (P.season < s)])
    idx = P.season == s
    P.loc[idx, "exp_move"] = m.predict(C.move_design(P[idx], med, FEAT))

# decision snapshot: first DK snapshot at or after 9 PM ET the night before (or first seen if later), 0.5 h+ before tip
P["night_before"] = pd.to_datetime(P.date) - pd.Timedelta(hours=3)          # 21:00 the previous day
D = P[(P.snap >= P.night_before) & (P.lead_h >= 0.5) & P.exp_move.notna()].sort_values("snap").groupby(["date", "home"]).head(1)
F = P[(P.lead_h >= 0.5) & P.exp_move.notna()].sort_values("snap").groupby(["date", "home"]).head(1)   # first seen (exploratory)

V = pd.read_csv("analysis/threshold_sweep_2026-11-04/nba_v4_preds.csv")
V["date"] = pd.to_datetime(V.date).dt.strftime("%Y-%m-%d")
V = V[["date", "home", "away", "v4"]]


def prep(X):
    X = X.merge(V, on=["date", "home", "away"], how="inner").copy()
    X["mkt_exp_close"] = X.dk_now + X.exp_move
    return X


D, F = prep(D), prep(F)


def ols(X, cols):
    A = np.c_[np.ones(len(X)), X[cols].to_numpy(float)]
    return np.linalg.lstsq(A, X.final_total.to_numpy(float), rcond=None)[0]


def apply(b, X, cols):
    return np.c_[np.ones(len(X)), X[cols].to_numpy(float)] @ b


def grade(X, edge, thr):
    S = X[np.abs(edge) >= thr].copy(); e = edge[np.abs(edge) >= thr]
    if not len(S): return {"n": 0}
    over = e > 0
    clv = np.where(over, S.dk_close_point - S.dk_now, S.dk_now - S.dk_close_point)
    win = np.where(over, S.final_total > S.dk_now, S.final_total < S.dk_now); push = S.final_total == S.dk_now
    u = np.where(push, 0, np.where(win, [am_units(p) for p in np.where(over, S.price_o, S.price_u)], -1.0))
    return {"n": int(len(S)), "overs": int(over.sum()), "clv": round(float(clv.mean()), 2),
            "clv_se": round(float(clv.std() / np.sqrt(len(clv))), 2), "units": round(float(u.sum()), 1),
            "roi": round(float(u.sum() / len(S)), 3), "win": round(float(win[~push].mean()), 3)}


rep = {"games": {"decision_9pm": D.season.value_counts().sort_index().to_dict(), "first_seen": F.season.value_counts().sort_index().to_dict()}}
FULL = ["v4", "mkt_exp_close"]; NOMOVE = ["v4", "dk_now"]
for lab, X in (("decision_9pm", D), ("first_seen", F)):
    tr, te = X[X.season.isin([2024, 2025])], X[X.season == 2026]
    b = ols(tr, FULL); b0 = ols(tr, NOMOVE)
    r = rep[lab] = {"weights_full": dict(zip(["a"] + FULL, np.round(b, 3).tolist())),
                    "weights_no_move": dict(zip(["a"] + NOMOVE, np.round(b0, 3).tolist()))}
    for season in (2025, 2026):
        S = X[X.season == season]
        fair = apply(b, S, FULL); fair0 = apply(b0, S, NOMOVE)
        mae = lambda p: round(float(np.abs(S.final_total - p).mean()), 3)
        r[f"mae_{season}"] = {"blend": mae(fair), "blend_no_move": mae(fair0), "v4": mae(S.v4), "dk_now": mae(S.dk_now),
                              "dk_close": mae(S.dk_close_point), "dk_now+exp_move": mae(S.mkt_exp_close)}
        for thr in (1.5, 2.0, 3.0):
            tag = "PREREG" if (lab == "decision_9pm" and season == 2026 and thr == 2.0) else "exploratory"
            r[f"blend_{season}_thr{thr}"] = {**grade(S, fair - S.dk_now.to_numpy(), thr), "status": tag}
        r[f"blend_no_move_{season}_thr2.0"] = grade(S, fair0 - S.dk_now.to_numpy(), 2.0)
        r[f"BASELINE_v4_{season}_thr2.5"] = grade(S, S.v4.to_numpy() - S.dk_now.to_numpy(), 2.5)
        r[f"v4_{season}_thr3.0"] = grade(S, S.v4.to_numpy() - S.dk_now.to_numpy(), 3.0)
        r[f"movement_alone_{season}_thr1.5"] = grade(S, S.exp_move.to_numpy(), 1.5)
    # test bets on file
    S = X[X.season == 2026].copy(); S["fair"] = apply(b, S, FULL); S["edge"] = S.fair - S.dk_now
    if lab == "decision_9pm":
        S[np.abs(S.edge) >= 2.0][["date", "home", "away", "snap", "lead_h", "dk_now", "v4", "exp_move", "fair", "edge",
                                  "dk_close_point", "final_total"]].to_csv(OUT + "blend_bets_2025_26_reach.csv", index=False)
json.dump(rep, open(OUT + "blend_results_reach.json", "w"), indent=1)
print(json.dumps(rep, indent=1))

# ---- live weights: refit on all three seasons (2023-24..2025-26) at the 9 PM decision moment
bl = ols(D, FULL)
live = dict(version="blend v1", fit_on="2023-24..2025-26, decision = first DK snapshot at/after 9 PM ET the night before",
            a=float(bl[0]), w_v4=float(bl[1]), w_mkt_exp_close=float(bl[2]), bet_edge=2.0, n=int(len(D)),
            prereg="research/market_models/STEP4_BLEND_PREREG.md", test_2025_26=rep["decision_9pm"]["blend_2026_thr2.0"])
json.dump(live, open("data/blend_v1_reach.json", "w"), indent=1)
print("live blend weights:", {k: round(v, 3) for k, v in live.items() if k in ("a", "w_v4", "w_mkt_exp_close")})
