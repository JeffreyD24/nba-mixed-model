"""Fixes for the NBA spread model from the autopsy, each weight fit only on the OTHER two seasons (2023-24..2025-26):
  home   = shift for home court (model's home edge too big)
  inj    = extra weight on injured value at the open (model under-penalizes it)
  roster = roster strength now vs what the team played with so far (trades, buyouts, returns; analysis/roster_strength.py)
  form   = last-10 margin form (already in test tracking)
Bets at the opener, edge 3+, both teams 10+ games.  python analysis/spread_fixes.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.argv = ["x", W]
exec(open(os.path.join(W, "analysis", "form_adjust.py")).read().split("rows = []\nfor mk")[0])
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
c_inj = ["home_miss_off_open", "home_miss_def_open", "away_miss_off_open", "away_miss_def_open"]
D = P.merge(T[["date", "home", "away"] + c_inj], on=["date", "home", "away"], how="left")
R = pd.read_csv(os.path.join(W, "analysis", "roster_strength.csv"))
for side in ("home", "away"):
    D = D.merge(R[["date", "team", "delta"]].rename(columns={"team": side, "delta": f"{side}_rdelta"}), on=["date", side], how="left")
D["f_home"] = 1.0
D["f_inj_off"] = D.away_miss_off_open - D.home_miss_off_open          # + = home healthier on offense
D["f_inj_def"] = D.away_miss_def_open - D.home_miss_def_open
D["f_roster"] = (D.home_rdelta - D.away_rdelta).fillna(0)
D["f_form"] = D.sp_mg_10.fillna(0)
D["late"] = pd.to_datetime(D.date).dt.month.isin([2, 3, 4])
D = D.dropna(subset=c_inj)
y = D.margin - D.pred_margin; res = D.margin + D.open_spread
VARIANTS = {"current model": [], "home": ["f_home"], "injuries": ["f_inj_off", "f_inj_def"], "roster": ["f_roster"],
            "form": ["f_form"], "roster+form": ["f_roster", "f_form"], "home+injuries": ["f_home", "f_inj_off", "f_inj_def"],
            "home+injuries+roster": ["f_home", "f_inj_off", "f_inj_def", "f_roster"],
            "all four": ["f_home", "f_inj_off", "f_inj_def", "f_roster", "f_form"]}
def u_(r): w, l = (r > 0).sum(), (r < 0).sum(); return w + l, w / max(w + l, 1), w * 100 / 110 - l
rows = []
for name, fs in VARIANTS.items():
    adj = D.pred_margin.copy(); coefs = {}
    for s in SEAS:
        te = D.season == s; tr = ~te
        if fs:
            X = D.loc[tr, fs].values; b = np.linalg.lstsq(X, y[tr].values, rcond=None)[0]
            adj[te] = D.pred_margin[te] + D.loc[te, fs].values @ b; coefs[s] = np.round(b, 2).tolist()
    e = adj + D.open_spread; m = e.abs() >= 3; r = np.sign(e) * res
    row = dict(variant=name)
    for s in SEAS: n, wp, u = u_(r[m & (D.season == s)]); row[f"{s}"] = f"{u:+.1f}"
    for lab, k in (("Oct-Jan", ~D.late), ("Feb-Apr", D.late)): n, wp, u = u_(r[m & k]); row[lab] = f"{n} {wp:.1%} {u:+.1f}u"
    hd = (e > 0) & (D.open_spread > 0); n, wp, u = u_(r[m & hd]); row["home dogs"] = f"{n} {u:+.1f}u"
    n, wp, u = u_(r[m]); row["total"] = f"{n} {wp:.1%} {u:+.1f}u"
    row["MAE"] = round(float((adj - D.margin).abs().mean()), 3); row["weights"] = coefs.get(2026)
    rows.append(row)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
print(pd.DataFrame(rows).to_string(index=False))
