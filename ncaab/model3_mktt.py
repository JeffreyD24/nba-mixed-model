"""MKT-T: market-implied ratings with ridge tuned on 2009-11 SBR openers (addendum, ncaab/research/MODEL3_PREREG_2026-11-05.md).
  python ncaab/model3_mktt.py WORKDIR -> adds MKTT_m / MKTT_t to ncaab/data/model3_preds.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
src = open(os.path.join(W, "ncaab", "model3.py")).read().split("out = G.copy()")[0]
ns = {"__name__": "m3t"}; sys.argv = ["x", W]; exec(src, ns); G, walk = ns["G"], ns["ns"]["walk"]; ns["ns"]["TGT"] = ("imp_h", "imp_a", "fit_mkt")
seas = list(range(2008, 2012)); idx = G.season.isin(seas).values; g = G[idx]
ok_o = g.open_sp.notna() & g.close_sp.notna() & ((g.open_sp - g.close_sp).abs() < 6) & g.season.isin([2009, 2010, 2011])
best = None
for r in (0.05, 0.2, 0.5, 1, 2):
    m, t = walk(seas, ridge=r); e = np.sqrt(np.mean((m[ok_o.values] + g.open_sp[ok_o].values) ** 2)); et = np.sqrt(np.mean((t[ok_o.values] - g.open_tot[ok_o].values) ** 2))
    print(f"ridge {r}: opener RMSE spread {e:.2f} total {et:.2f}", flush=True)
    if best is None or e + et < best[1]: best = (r, e + et)
print("chosen ridge", best[0])
m, t = walk(sorted(G.season.unique()), ridge=best[0])
P = pd.read_csv(os.path.join(W, "ncaab", "data", "model3_preds.csv"), low_memory=False)
assert len(P) == len(G) and (P.espn_id.values == G.espn_id.values).all()
P["MKTT_m"], P["MKTT_t"] = m, t; P.to_csv(os.path.join(W, "ncaab", "data", "model3_preds.csv"), index=False)
