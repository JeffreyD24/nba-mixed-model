"""NFL: weight the models deserve against DraftKings' opener (Nov 3, 2026, job 3 of research/HANDOFF_TO_OPUS.md).
Reuses the exact rebuild in analysis/nfl_weather_leak_test.py (team model, player model, with and without game-time weather).
  shrunk = opener + w x (model - opener); w = OLS slope of (result - opener) on (model - opener), through the origin.
Rule NOT tuned: bet when the shrunk number beats -110 (|shrunk edge| >= 0.0597 x sd of the misses). Each season uses w and sd
fit on the other seasons. Totals use the v2 number (average of team and player models), weeks 5-14, as live.
  python analysis/nfl_shrink_weights.py WORKDIR NFL_REPO   -> analysis/nfl_shrink_weights_output.txt, NFL_REPO/data/shrink_weights.json"""
import os, sys, glob, io, contextlib, json
import numpy as np, pandas as pd
from scipy.stats import norm
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
src = open(os.path.join(W, "analysis", "nfl_weather_leak_test.py")).read().split("\nout = []\n")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
Z = norm.ppf(110 / 210); out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
def slope(x, y):
    m = ~(np.isnan(x) | np.isnan(y)); x, y = x[m], y[m]; b = (x @ y) / (x @ x); r = y - b * x
    return b, np.sqrt(r @ r / (len(x) - 1) / (x @ x)), np.std(y - b * x, ddof=1), len(x)
cfg = {}
SPECS = (("totals v2, game-time weather (leaks)", lambda D: (D.pt_w + D.A_w) / 2, "tot", True),
         ("totals v2, no weather (honest floor)", lambda D: (D.pt_n + D.A_n) / 2, "tot", True),
         ("spreads, team model", lambda D: D.pm, "sp", False))
for lab, num, mk, wk in SPECS:
    D = P[P.week.between(5, 14)] if wk else P
    if mk == "tot":
        line, act = D.o_tot, D.tp; model = num(D)
    else:
        line = -D.o_sp; act = D.margin; model = num(D)          # o_sp = home line, so -o_sp = line-implied home margin
    x = (model - line).values.astype(float); y = (act - line).values.astype(float)
    b, se, sd, n = slope(x, y)
    per = " | ".join(f"{s}: {slope(x[D.season.values == s], y[D.season.values == s])[0]:+.2f}" for s in SEAS)
    say(f"\n== {lab}: weight vs opener {b:+.2f} (+/- {se:.2f}), n={n}\n   by season: {per}")
    tot = {"shrunk": [0, 0, 0.0], "raw": [0, 0, 0.0]}
    raw_thr = 2.0 if mk == "tot" else 3.0
    for s in SEAS:
        tr, te = D.season.values != s, D.season.values == s
        ws, _, sds, _ = slope(x[tr], y[tr]); thr = Z * sds
        for key, e, t in (("shrunk", ws * x[te], thr), ("raw", x[te], raw_thr)):
            m = (np.abs(e) >= t) & ~np.isnan(y[te]); r = np.sign(e[m]) * y[te][m]; w_, l_ = int((r > 0).sum()), int((r < 0).sum())
            tot[key][0] += w_; tot[key][1] += l_; tot[key][2] += w_ * 100 / 110 - l_
    for key, lab2 in (("shrunk", "shrunk, bet when it beats -110"), ("raw", f"live-style raw edge {raw_thr:g}+")):
        w_, l_, u_ = tot[key]; say(f"   out of season, {lab2}: {w_}-{l_} ({w_ / max(w_ + l_, 1):.1%}) {u_:+.1f}u")
    cfg[lab] = dict(weight=round(float(b), 3), weight_se=round(float(se), 3), resid_sd=round(float(sd), 2),
                    shrunk_edge_threshold=round(float(Z * sd), 2), raw_edge_equivalent=round(float(Z * sd / b), 2) if b > 0 else None)
cfg["fit"] = dict(seasons="2020-2025", lines="DraftKings opener", set_on="2026-11-03", z=round(float(Z), 4),
                  note="totals fit on weeks 5-14 (live window); spreads all weeks. Spreads/totals are test-only or v2 live; nothing changed.")
json.dump(cfg, open(os.path.join(N, "data", "shrink_weights.json"), "w"), indent=1)
open(os.path.join(W, "analysis", "nfl_shrink_weights_output.txt"), "w").write("\n".join(out) + "\n")
