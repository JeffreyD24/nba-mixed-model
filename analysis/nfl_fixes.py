"""NFL fixes from the autopsy, each weight fit leaving the test season out (2020-2025), graded at the opener (DraftKings from
the odds history 2020-23, backtest opener 2024-25), edge 3+, early-week model.
  weather (totals): wind mph and cold (degrees below 40) for outdoor games (nflverse schedule; domes/closed roofs = 0)
  qb (spreads): each team's QB-out flag (the model may over-penalize a missing QB)
  home (spreads): home-field shift;  late (both): week 15+ shrink toward the line
  python analysis/nfl_fixes.py WORKDIR NFL_REPO"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
src = open(os.path.join(W, "analysis", "nfl_autopsy.py")).read().split("def u(s)")[0].split("W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])")[1]
exec(src)
V = pd.read_csv(os.path.join(N, "data", "nflverse_games.csv"))
ab = {"LA": "lar", "LV": "lv", "OAK": "lv", "SD": "lac", "STL": "lar", "WAS": "wsh", "JAX": "jax"}
code = lambda t: ab.get(t, str(t).lower())
V["home"] = V.home_team.map(code); V["away"] = V.away_team.map(code); V["date"] = V.gameday
V["outdoor"] = V.roof.isin(["outdoors", "open"])
V["wind_x"] = np.where(V.outdoor, V.wind.fillna(V.wind.median()), 0.0)
V["cold_x"] = np.where(V.outdoor, (40 - V.temp.fillna(60)).clip(lower=0), 0.0)
P = P.merge(V[["date", "home", "away", "wind_x", "cold_x", "div_game", "outdoor"]], on=["date", "home", "away"], how="left")
print("games matched to nflverse weather:", P.wind_x.notna().mean().round(3))
P[["wind_x", "cold_x"]] = P[["wind_x", "cold_x"]].fillna(0)
P["qb_h"] = P.home_qb_miss_early.fillna(0).astype(float); P["qb_a"] = P.away_qb_miss_early.fillna(0).astype(float)
P["late"] = (P.week >= 15).astype(float); P["one"] = 1.0
SEAS = sorted(P.season.unique())
def grade(pred, line, y, sign):
    e = pred - line if sign > 0 else pred + line; r = (y - line) if sign > 0 else (y + line)
    m = e.abs() >= 3; rr = np.sign(e[m]) * r[m]; w, l = (rr > 0).sum(), (rr < 0).sum(); return w + l, w, w * 100 / 110 - l
def run(mk, feats, late_shrink=False):
    base = P.pt if mk == "tot" else P.pm; y = P.tp if mk == "tot" else P.margin
    line = P.o_tot if mk == "tot" else P.o_sp; sign = 1 if mk == "tot" else -1
    mkt = line if mk == "tot" else -line
    adj = base.copy(); out = []; tot_u = 0; tot_n = 0; tot_w = 0
    for s in SEAS:
        te = P.season == s; tr = ~te
        a = base[te].copy()
        if feats:
            X = P.loc[tr, feats].values; b = np.linalg.lstsq(X, (y - base)[tr].values, rcond=None)[0]
            a = a + P.loc[te, feats].values @ b
        if late_shrink:     # week 15+: weight on the model vs the line, fit on other seasons
            k_tr = tr & (P.late == 1)
            d_ = (base[k_tr] - mkt[k_tr]); r_ = (y[k_tr] - mkt[k_tr]); c = float((d_ * r_).sum() / (d_ * d_).sum())
            lt = te & (P.late == 1); a[lt[te].values] = mkt[lt] + c * (a[lt[te].values] - mkt[lt])
        adj[te] = a
        n, w, u = grade(adj[te], line[te], y[te], sign); out.append(f"{u:+.1f}"); tot_u += u; tot_n += n; tot_w += w
    return " ".join(out) + f" | {tot_n} bets {tot_w / max(tot_n, 1):.1%} {tot_u:+.1f}u  MAE {np.abs(adj - y).mean():.3f}"
print("seasons", SEAS)
print("TOTALS")
for lab, f, ls in (("current", [], False), ("weather (wind + cold)", ["wind_x", "cold_x"], False), ("wind only", ["wind_x"], False),
                   ("late-season shrink", [], True), ("weather + late shrink", ["wind_x", "cold_x"], True)):
    print(f"  {lab:28s}", run("tot", f, ls))
print("SPREADS")
for lab, f, ls in (("current", [], False), ("home shift", ["one"], False), ("QB out (both teams)", ["qb_h", "qb_a"], False),
                   ("late-season shrink", [], True), ("home + QB", ["one", "qb_h", "qb_a"], False), ("home + QB + late shrink", ["one", "qb_h", "qb_a"], True)):
    print(f"  {lab:28s}", run("sp", f, ls))
