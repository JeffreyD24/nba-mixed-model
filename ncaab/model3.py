"""NCAAM Model 3: predictions for three targets (ncaab/research/MODEL3_PREREG_2026-11-05.md).
  python ncaab/model3.py WORKDIR -> ncaab/data/model3_preds.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
src = open(os.path.join(W, "ncaab", "model2_tournament.py")).read().split("SEAS = sorted")[0]
src = src.replace("hp, ap = S.home_pts.values.astype(float), S.away_pts.values.astype(float)", "hp, ap = S[TGT[0]].values.astype(float), S[TGT[1]].values.astype(float)")
src = src.replace("today = np.where(dates == d)[0]; past = np.where(dates < d)[0]", "today = np.where(dates == d)[0]; past = np.where((dates < d) & S[TGT[2]].values)[0]")
src = src.replace("np.mean(yh[:100])", "np.nanmean(yh[:300])")
ns = {"__name__": "m3"}; sys.argv = ["x", W, "--live-rule"]; exec(src, ns)
G = ns["G"]
G["fit_all"] = True
# market-implied team points from the closing lines (SBR openers 6+ from the close are bad quotes; closes kept)
G["imp_h"] = (G.close_tot - G.close_sp) / 2; G["imp_a"] = (G.close_tot + G.close_sp) / 2
G["fit_mkt"] = G.imp_h.notna() & G.imp_a.notna() & (G.close_tot > 90)
SEAS = sorted(G.season.unique())
out = G.copy()
for name, tgt, kw in (("M2", ("home_pts", "away_pts", "fit_all"), dict(level_half=14)), ("M8", ("home_pts", "away_pts", "fit_all"), dict(ridge=10.0, cridge=10.0)),
                      ("MKT", ("imp_h", "imp_a", "fit_mkt"), {})):
    ns["TGT"] = tgt
    m, t = ns["walk"](SEAS, **kw); out[f"{name}_m"], out[f"{name}_t"] = m, t; print("ran", name, flush=True)
out.to_csv(os.path.join(W, "ncaab", "data", "model3_preds.csv"), index=False)
