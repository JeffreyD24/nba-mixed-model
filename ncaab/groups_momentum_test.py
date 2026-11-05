"""No-hindsight 'market underrated / overrated' teams (addendum in ncaab/research/GROUPS_PREREG_2026-11-05.md).
  python ncaab/groups_momentum_test.py WORKDIR -> ncaab/research/groups_momentum_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
G = pd.read_csv(os.path.join(W, "ncaab", "data", "groups_games.csv"), low_memory=False)
G = G[G.close_sp.notna() & G.home_loc.notna() & G.away_loc.notna()].copy()
hc = np.sign(G.home_pts - G.away_pts + G.close_sp)
L = pd.concat([pd.DataFrame(dict(season=G.season, t=G.home_loc, c=hc)), pd.DataFrame(dict(season=G.season, t=G.away_loc, c=-hc))])
L = L[L.c != 0]; rec = L.groupby(["season", "t"]).c.agg(cov=lambda x: (x > 0).sum(), n="size").reset_index()
def groups(s):
    p = rec[rec.season.isin([s - 2, s - 1])].groupby("t")[["cov", "n"]].sum(); p = p[p.n >= 40]; p["r"] = p["cov"] / p.n
    p = p.sort_values("r"); return set(p.index[-25:]), set(p.index[:25])
rows = []
for s in sorted(G.season.unique()):
    if s < 2010 or s > 2026: continue
    U, O = groups(s); g = G[G.season == s]
    for lab, S, sgn in (("back U25", U, 1), ("fade O25", O, -1)):
        h, a = g.home_loc.isin(S), g.away_loc.isin(S); k = h ^ a
        r = np.where(h[k], hc[g.index][k], -hc[g.index][k]) * sgn; r = r[r != 0]
        rows += [dict(cell=lab, season=s, win=int((r > 0).sum()), n=len(r))]
R = pd.DataFrame(rows)
for lab, g in R.groupby("cell"):
    for per, k in (("discovery 2010-2018", g.season <= 2018), ("holdout 2019-2026", g.season >= 2019), ("DK 2024-2026", g.season >= 2024)):
        w, n = g[k].win.sum(), g[k].n.sum(); p = w / n
        say(f"  {lab:9s} {per:20s} {n:5d} bets {p:.1%} z {(p - .5) / np.sqrt(.25 / n):+.2f} units {w * 100 / 110 - (n - w):+.1f}")
    say("     by season: " + " ".join(f"{s % 100:02d}:{w / n:.0%}" for s, w, n in zip(g.season, g.win, g.n)))
open(os.path.join(W, "ncaab", "research", "groups_momentum_output.txt"), "w").write("\n".join(out) + "\n")
