"""Shrink Model 1 toward DraftKings' opener, with the one-day lag fixed (Nov 3, 2026, job 3 of research/HANDOFF_TO_OPUS.md).
  shrunk = line + w x (model - line)
w = OLS slope of (result - line) on (model - line), through the origin. The bet rule is NOT tuned: bet when the shrunk number
says the bet wins more often than the -110 break-even (52.38%), i.e. |shrunk edge| >= z x sd with z = 0.0597 (normal),
sd = spread of (result - shrunk number) on the training seasons. Each test season uses w and sd fit on the OTHER two seasons.
Note: shrinking does not reorder bets within a market, so this rule equals Model 1 with a raw-edge cutoff of z x sd / w.
What it adds is a principled cutoff and an honest estimate of the true edge (and win chance) of every bet.
Input: _tmp/model1_lag1_dk_open.csv from analysis/lag_leak_test.py.   python analysis/shrink_weights.py WORKDIR"""
import os, sys, json
import numpy as np, pandas as pd
from scipy.stats import norm
W = os.path.abspath(sys.argv[1])
P = pd.read_csv(os.path.join(W, "_tmp", "model1_lag1_dk_open.csv"))
Z = norm.ppf(110 / 210)          # 0.0597: shrunk edge in sd units needed to beat -110
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

def parts(D, mk, line):
    L = -D[f"{line}_spread"] if mk == "spread" else D[f"{line}_total"]      # line-implied home margin / total
    pred = D.pred_margin if mk == "spread" else D.pred_total
    act = D.home_pts - D.away_pts if mk == "spread" else D.home_pts + D.away_pts
    return (pred - L).values, (act - L).values

def slope(x, y):
    m = ~(np.isnan(x) | np.isnan(y)); x, y = x[m], y[m]
    b = (x @ y) / (x @ x); r = y - b * x; return b, np.sqrt(r @ r / (len(x) - 1) / (x @ x)), np.sqrt(r @ r / (len(x) - 1)), len(x)

def grade(edge, res, thr):
    m = (np.abs(edge) >= thr) & ~np.isnan(res); r = np.sign(edge[m]) * res[m]
    w, l = int((r > 0).sum()), int((r < 0).sum()); return w + l, w / max(w + l, 1), w * 100 / 110 - l

P = P.rename(columns={"spread": "close_spread", "total": "close_total"})
SEAS = (2024, 2025, 2026)
cfg = {}
for mk in ("spread", "total"):
    say(f"\n== {mk.upper()}  (Model 1, live morning lock = results through two nights before)")
    for line in ("open", "close"):
        x, y = parts(P, mk, line); b, se, sd, n = slope(x, y)
        per = []
        for s in SEAS:
            xs, ys = parts(P[P.season == s], mk, line); per.append(f"{s}: {slope(xs, ys)[0]:+.2f}")
        say(f"  weight vs {line:5s}: {b:+.2f} (+/- {se:.2f}), n={n}   " + " | ".join(per))
    say("  Out of season (w and sd fit on the other two seasons), graded at the opener:")
    tot = {"shrunk": [0, 0, 0.0], "raw3": [0, 0, 0.0]}
    for s in SEAS:
        tr, te = P[P.season != s], P[P.season == s]
        x, y = parts(tr, mk, "open"); w, _, _, _ = slope(x, y)
        sd = np.nanstd(y - w * x, ddof=1); thr = Z * sd
        xt, yt = parts(te, mk, "open")
        a = grade(w * xt, yt, thr); b3 = grade(xt, yt, 3.0)
        say(f"    {s}: w={w:.2f} sd={sd:.1f} -> bet when shrunk edge >= {thr:.2f} (raw edge >= {thr / w:.1f}):"
            f" {a[0]} bets {a[1]:.1%} {a[2]:+.1f}u   | Model 1 raw edge 3+: {b3[0]} bets {b3[1]:.1%} {b3[2]:+.1f}u")
        for k, v in (("shrunk", a), ("raw3", b3)):
            tot[k][0] += v[0]; tot[k][1] += v[1] * v[0]; tot[k][2] += v[2]
    for k, lab in (("shrunk", "shrunk rule"), ("raw3", "Model 1 edge 3+")):
        say(f"    all three: {lab}: {tot[k][0]} bets {tot[k][1] / max(tot[k][0], 1):.1%} {tot[k][2]:+.1f}u")
    # live setting: fit on all three seasons
    x, y = parts(P, mk, "open"); w, se, _, n = slope(x, y); sd = np.nanstd(y - w * x, ddof=1)
    cfg[mk] = dict(weight=round(float(w), 3), weight_se=round(float(se), 3), resid_sd=round(float(sd), 2),
                   shrunk_edge_threshold=round(float(Z * sd), 2), raw_edge_equivalent=round(float(Z * sd / w), 2), n_games=int(n))
    say(f"  LIVE SETTING (fit on 2023-24..2025-26): w = {w:.3f} (+/- {se:.3f}), sd {sd:.1f}, bet when shrunk edge >= {Z * sd:.2f}"
        f" (= raw edge >= {Z * sd / w:.1f})")
cfg["fit"] = dict(seasons="2023-24, 2024-25, 2025-26", lines="DraftKings opener (The Odds API history)",
                  model="Model 1 walk-forward with one-day lag (analysis/lag_leak_test.py)", set_on="2026-11-03", z=round(float(Z), 4))
json.dump(cfg, open(os.path.join(W, "data", "shrink_weights.json"), "w"), indent=1)
open(os.path.join(W, "analysis", "shrink_weights_output.txt"), "w").write("\n".join(out) + "\n")
