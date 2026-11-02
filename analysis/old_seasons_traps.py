"""Feb-Apr spread traps on 2009-10..2020-21 (no-injury Model 1, closing spreads; see old_seasons.py).
  python analysis/old_seasons_traps.py WORKDIR"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
P = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(W, "_tmp", "old_preds_*.csv")))], ignore_index=True)
P["date"] = pd.to_datetime(P.date).dt.strftime("%Y-%m-%d")
EAST = {"atl", "bos", "bkn", "cha", "chi", "cle", "det", "ind", "mia", "mil", "ny", "orl", "phi", "tor", "wsh"}
cat = {}
for s, S in P.groupby("season"):
    S = S.sort_values("date")
    for d in sorted(S.date.unique()):
        past = S[S.date < d]
        if len(past) < 150: continue
        rec = {}
        for r in past.itertuples():
            for t, w in ((r.home, r.home_pts > r.away_pts), (r.away, r.away_pts > r.home_pts)):
                a, b = rec.get(t, (0, 0)); rec[t] = (a + int(w), b + int(not w))
        for conf in (True, False):
            c = sorted([(t, a, b) for t, (a, b) in rec.items() if (t in EAST) == conf], key=lambda x: -x[1] / max(x[1] + x[2], 1))
            if len(c) < 10: continue
            w10, l10 = c[9][1], c[9][2]
            for i, (t, a, b) in enumerate(c, 1):
                gb = ((w10 - l10) - (a - b)) / 2
                cat[(d, t)] = "top" if i <= 4 else "middle" if i <= 10 else "bubble" if (i <= 12 and gb <= 4) else "tanking"
P["h_cat"] = [cat.get((d, t)) for d, t in zip(P.date, P.home)]; P["a_cat"] = [cat.get((d, t)) for d, t in zip(P.date, P.away)]
P["margin"] = P.home_pts - P.away_pts; P["e"] = P.pred_margin + P.spread
B = P[(P.e.abs() >= 3) & P.h_cat.notna()].copy(); hb = B.e > 0
B["res"] = np.sign(B.e) * (B.margin + B.spread); B = B[B.res != 0]; hb = B.e > 0
B["won"] = B.res > 0; B["our"] = np.where(hb, B.h_cat, B.a_cat); B["opp"] = np.where(hb, B.a_cat, B.h_cat)
B["home_dog"] = hb & (B.spread > 0)
m = pd.to_datetime(B.date).dt.month
B["late"] = np.where(B.season == 2021, m.isin([4, 5]), m.isin([2, 3, 4]))           # 2020-21 ran Dec-May
B = B[~((B.season == 2020) & (pd.to_datetime(B.date) >= "2020-03-12"))]            # 2019-20 bubble games excluded
def s_(g):
    n = len(g); w = g.won.sum(); pos = sum((lambda x: x.won.sum() * 100 / 110 - (len(x) - x.won.sum()) > 0)(g[g.season == s]) for s in g.season.unique())
    return f"{n:5d} bets {w / max(n, 1):.1%} {w * 100 / 110 - (n - w):+7.1f}u  (positive in {pos} of {g.season.nunique()} seasons)"
print("Old seasons 2009-10..2020-21, no-injury Model 1, CLOSING spreads, edge 3+")
for h, H in (("Oct-Jan", B[~B.late]), ("Feb-Apr", B[B.late])):
    print(f"\n{h}: all {s_(H)}")
    trap = (H.our == "tanking") | (H.opp == "middle")
    for lab, k in (("bet a tanking team", H.our == "tanking"), ("bet against a playoff-spot (5-10) team", H.opp == "middle"),
                   ("bet against a top-4 team", H.opp == "top"), ("home underdogs", H.home_dog),
                   ("TRAPS (tanking or vs playoff spot)", trap), ("outside the traps", ~trap), ("outside the traps, no home dogs", ~trap & ~H.home_dog)):
        print(f"  {lab:40s} {s_(H[k])}")
