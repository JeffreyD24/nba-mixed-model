"""Predictions for the NCAAM three-target tournament (ncaab/research/THREE_TARGETS_PREREG_2026-11-05.md): M1, M2, M8 on results and
MKT on the points implied by past closing lines. All walk-forward, pre-game-known team rule.
  python ncaab/three_targets_preds.py WORKDIR -> ncaab/data/three_targets_preds.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
src = open(os.path.join(W, "ncaab", "model2_tournament.py")).read().split("SEAS = sorted")[0]
ns = {"__name__": "m2"}; sys.argv = ["x", W, "--live-rule"]; exec(src, ns)
G = ns["G"]; SEAS = sorted(G.season.unique())
for k, kw in (("M1", {}), ("M2", dict(level_half=14)), ("M8", dict(ridge=10.0, cridge=10.0))):
    G[f"{k}_m"], G[f"{k}_t"] = ns["walk"](SEAS, **kw); print("ran", k, flush=True)
# MKT: same model fitted to the points implied by each past game's closing line (games without a close are left out of the fit)
C = G[G.close_sp.notna() & G.close_tot.notna()].copy().reset_index()
C["home_pts"] = (C.close_tot - C.close_sp) / 2; C["away_pts"] = (C.close_tot + C.close_sp) / 2
ns["G"] = C; m, t = ns["walk"](sorted(C.season.unique())); C["MKT_m"], C["MKT_t"] = m, t
G = G.merge(C[["espn_id", "MKT_m", "MKT_t"]], on="espn_id", how="left"); print("ran MKT", flush=True)
G.to_csv(os.path.join(W, "ncaab", "data", "three_targets_preds.csv"), index=False); print("saved", len(G))
