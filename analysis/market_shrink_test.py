"""How much weight should the NBA model get versus the market line? OLS of (actual - line-implied) on (model - line-implied).
slope ~ 1: model adds as much as it claims; ~ 0: line already has it all (shrink hard toward the market). Opening and closing lines."""
import sys, numpy as np, pandas as pd
P = pd.read_csv(sys.argv[1])
def ols(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float); m = ~(np.isnan(x) | np.isnan(y)); x, y = x[m], y[m]
    b = (x * y).sum() / (x * x).sum(); r = y - b * x; se = np.sqrt((r @ r) / (len(x) - 1) / (x * x).sum()); return b, se, len(x)
rows = []
for mk, pred, act, lines in (("spread", "pred_margin", "margin", (("open", "open_spread"), ("close", "spread"))),
                             ("total", "pred_total", "tot", (("open", "open_total"), ("close", "total")))):
    for tag, lc in lines:
        L = -P[lc] if mk == "spread" else P[lc]
        d = P[pred] - L; y = P[act] - L
        b, se, n = ols(d, y); rows.append((mk, tag, "ALL", n, b, se))
        for s, g in P.assign(_d=d, _y=y).groupby("season"):
            b, se, n = ols(g._d, g._y); rows.append((mk, tag, int(s), n, b, se))
print("seasons in file:", sorted(P.season.unique()))
print(f"{'market':7}{'line':6}{'season':8}{'n':>6}{'weight on model':>17}{'+/- se':>9}")
for r in rows: print(f"{r[0]:7}{r[1]:6}{str(r[2]):8}{r[3]:>6}{r[4]:>17.2f}{r[5]:>9.2f}")
