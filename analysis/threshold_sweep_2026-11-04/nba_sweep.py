# Run from the repo root: python analysis/threshold_sweep_2026-11-04/nba_v4_preds.py . (writes nba_v4_preds.csv here, then run nba_sweep.py and nba_shop.py from this folder)
import numpy as np, pandas as pd
P = pd.read_csv("nba_v4_preds.csv"); P["date"] = pd.to_datetime(P.date)
P["y"] = P.home_pts + P.away_pts - P.open_total; P["move"] = P.close_total - P.open_total
e = P.v4 - P.open_total
rng = np.random.default_rng(7)
print("PRE-REGISTERED: primary = avg CLV (pts toward bet by close); secondary = units at -110; seasons 2023-24..2025-26 at DK openers.\n")
print(f"{'cutoff':>6} {'bets':>5} {'win%':>6} {'units':>7} {'ROI':>6} {'CLV':>5}  by season (units)   | marginal band vs next cutoff")
cuts = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
for i, c in enumerate(cuts):
    k = e.abs() >= c; r = np.sign(e[k]) * P.y[k]; r = r[r != 0]
    u = np.where(r > 0, 100/110, -1.0); clv = (np.sign(e[k]) * P.move[k]).mean()
    bys = " ".join(f"{str(s)[2:]}:{u[P.season[r.index] == s].sum():+.1f}" for s in (2024, 2025, 2026))
    band = ""
    if i + 1 < len(cuts):
        kb = (e.abs() >= c) & (e.abs() < cuts[i+1]); rb = np.sign(e[kb]) * P.y[kb]; rb = rb[rb != 0]; ub = np.where(rb > 0, 100/110, -1.0)
        band = f"| {c}-{cuts[i+1]}: {len(ub)} bets {np.mean(ub > 0):.1%} {ub.sum():+.1f}u CLV {(np.sign(e[kb]) * P.move[kb]).mean():+.2f}"
    print(f"{c:6.1f} {len(u):5d} {np.mean(u > 0):6.1%} {u.sum():+7.1f} {u.mean():+6.1%} {clv:+5.2f}  {bys}  {band}")
B = P[e.abs() >= 3].copy(); B["sg"] = np.sign(e[e.abs() >= 3]); B.to_csv("nba_v4_bets3.csv", index=False)
