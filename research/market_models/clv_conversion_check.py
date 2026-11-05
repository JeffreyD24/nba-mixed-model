"""Exploratory (after the step 3 result): does a point of CLV turn into wins at the rate the break-even assumes?
Hindsight bet on every game: at DK's first-seen total, take the side the line later moved toward.
CLV = |close - first seen|. Expected win rate if the close is a fair number with result sd 18: Phi(CLV / 18).
"""
import numpy as np, pandas as pd
from scipy.stats import norm
G = pd.read_csv("research/market_models/opener_data.csv.gz").dropna(subset=["dk_open_point", "dk_close_point"])
mv = G.dk_close_point - G.dk_open_point
G = G[mv != 0].assign(mv=mv)
over = G.mv > 0
win = np.where(over, G.final_total > G.dk_open_point, G.final_total < G.dk_open_point)
push = G.final_total == G.dk_open_point
G = G.assign(clv=G.mv.abs(), win=win, push=push)
G["bucket"] = pd.cut(G.clv, [0, 1, 2, 3, 5, 99], right=True)
t = G[~G.push].groupby(["bucket"], observed=True).agg(n=("win", "size"), win=("win", "mean"), clv=("clv", "mean"))
t["expected"] = norm.cdf(t.clv / 18.0)
t["se"] = np.sqrt(t.win * (1 - t.win) / t.n)
print(t.round(3).to_string())
by = G[~G.push].groupby("season").apply(lambda z: pd.Series({"n": len(z), "win": z.win.mean(), "exp": norm.cdf(z.clv / 18).mean()}))
print(by.round(3).to_string())
# slope: win prob per point of CLV (linear probability fit)
x = G[~G.push]; b = np.polyfit(x.clv, x.win.astype(float), 1)
print("win rate per point of CLV:", round(b[0], 4), "intercept", round(b[1], 3), "(fair-close assumption: ~0.022/pt, intercept 0.50)")
