"""Leakage check (Nov 3, 2026): NFL totals v2 graded at the OPENING total used ACTUAL game-time weather (nflverse temp/wind).
The opener posts about a week before kickoff, when nobody knows game-day wind; the market moves the total as forecasts firm up.
So the backtest partly credits the model with weather news the opener did not have.
No historical forecasts exist here, so this brackets the truth:
  game-time weather  = as backtested (upper bound, leaks)
  no weather         = both components refit without wind/cold (lower bound: no weather information at all)
A bet placed at the opener with a ~6-day forecast lands in between (wind forecasts that far out are weak).
Same rule as live v2: average of (team model + weather, week 15+ shrink) and (player model + its own weather), edge 2+, weeks 5-14.
  python analysis/nfl_weather_leak_test.py WORKDIR NFL_REPO   -> analysis/nfl_weather_leak_test_output.txt"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
argv = sys.argv[:]

# 1. player model features (G) exactly as analysis/nfl_player_model.py builds them
src = open(os.path.join(W, "analysis", "nfl_player_model.py")).read().split("out = []")[0].split(
    "W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])", 1)[1]
exec(src)
Gp = G.copy()
TF_W = ["one", "pass_sum", "rush_sum", "pace", "qbchg_s", "wind_x", "cold_x"]; TF_N = [c for c in TF_W if c not in ("wind_x", "cold_x")]
A = []
for s in range(2020, 2026):
    tr = Gp[(Gp.season < s) & (Gp.season >= 2018)]; te = Gp[Gp.season == s].copy()
    te["A_w"] = te[TF_W].values @ fit(tr, TF_W, "total_y"); te["A_n"] = te[TF_N].values @ fit(tr, TF_N, "total_y")
    A.append(te[["date", "home", "away", "A_w", "A_n"]])
A = pd.concat(A)

# 2. team model + weather + late shrink, exactly as analysis/nfl_totals_autopsy.py, and the same without weather
src = open(os.path.join(W, "analysis", "nfl_fixes.py")).read().split('print("seasons", SEAS)')[0].split(
    "W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])", 1)[1]
exec(src)
P = P.drop_duplicates(["date", "home", "away"]).reset_index(drop=True)
base, y, line = P.pt, P.tp, P.o_tot
def adjust(feats):
    adj = base.copy()
    for s in SEAS:
        te = P.season == s; tr = ~te
        a = base[te].copy()
        if feats:
            b = np.linalg.lstsq(P.loc[tr, feats].values, (y - base)[tr].values, rcond=None)[0]; a = base[te] + P.loc[te, feats].values @ b
        k_tr = tr & (P.late == 1); d_ = base[k_tr] - line[k_tr]; r_ = y[k_tr] - line[k_tr]; c = float((d_ * r_).sum() / (d_ * d_).sum())
        lt = te & (P.late == 1); a[lt] = line[lt] + c * (a[lt] - line[lt]); adj[te] = a
    return adj
P["pt_w"] = adjust(["wind_x", "cold_x"]); P["pt_n"] = adjust([])
P = P.merge(A, on=["date", "home", "away"], how="left")

out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
def grade(e, m):
    sg = np.sign(e[m]); r = sg * (P.tp[m] - P.o_tot[m]); w, l = int((r > 0).sum()), int((r < 0).sum())
    clv = (sg * (P.c_tot[m] - P.o_tot[m])).mean()
    return w + l, w / max(w + l, 1), w * 100 / 110 - l, clv
say("NFL totals v2 at DraftKings openers 2020-25, edge 2+, weeks 5-14 (live rule)")
for lab, t, a in (("game-time weather (as backtested)", "pt_w", "A_w"), ("no weather at all", "pt_n", "A_n"),
                  ("weather in team model only", "pt_w", "A_n"), ("weather in player model only", "pt_n", "A_w")):
    e = (P[t] + P[a]) / 2 - P.o_tot
    m = (e.abs() >= 2) & P.week.between(5, 14) & P[a].notna()
    n, wp, u, clv = grade(e, m)
    per = " ".join(f"{s % 100}:{grade(e, m & (P.season == s))[2]:+.1f}" for s in SEAS)
    say(f"  {lab:36s} {n:4d} bets {wp:.1%} {u:+6.1f}u  CLV {clv:+.2f} pts   [{per}]")
# how much did the market move totals toward the actual wind after the open? (the leak channel)
P["outdoor_w"] = (P.wind_x > 0)
o = P[P.outdoor_w & P.c_tot.notna() & P.o_tot.notna()]
say(f"\nOpen-to-close total move vs game-time wind (outdoor games): corr {np.corrcoef(o.wind_x, o.c_tot - o.o_tot)[0, 1]:+.3f};"
    f" wind 15+ mph: avg move {(o.c_tot - o.o_tot)[o.wind_x >= 15].mean():+.2f} pts (n={(o.wind_x >= 15).sum()}),"
    f" wind under 8: {(o.c_tot - o.o_tot)[o.wind_x < 8].mean():+.2f} pts")
open(os.path.join(W, "analysis", "nfl_weather_leak_test_output.txt"), "w").write("\n".join(out) + "\n")
