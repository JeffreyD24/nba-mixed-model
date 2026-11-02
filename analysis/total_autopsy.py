"""NBA totals autopsy: every live-model totals bet (luck + last-10 form) at the opener, edge 3+, 2023-24..2025-26, wins vs losses.
  python analysis/total_autopsy.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.argv = ["x", W]
exec(open(os.path.join(W, "analysis", "form_adjust.py")).read().split("rows = []\nfor mk")[0])
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
cols = ["home_miss_off_open", "home_miss_def_open", "away_miss_off_open", "away_miss_def_open", "home_miss_off", "away_miss_off",
        "home_miss_def", "away_miss_def", "home_n_out_open", "away_n_out_open", "total"]
D = P.merge(T[["date", "home", "away"] + cols], on=["date", "home", "away"], how="left")
P2 = pd.read_csv(os.path.join(W, "_tmp", "test_2024_games.csv"))[["date", "home", "away", "ov_close"]]
D = D.merge(P2, on=["date", "home", "away"], how="left"); D["close_t"] = np.where(D.season == 2024, D.ov_close, D.total)
P1 = pd.read_csv(os.path.join(W, "_tmp", "model1_open_preds.csv"))[["date", "home", "away", "b2b_home", "b2b_away"]]
P3 = pd.read_csv(os.path.join(W, "_tmp", "test_2024_games.csv"))[["date", "home", "away", "b2b_home", "b2b_away"]]
P1["date"] = pd.to_datetime(P1.date).dt.strftime("%Y-%m-%d")
D = D.merge(pd.concat([P1, P3]), on=["date", "home", "away"], how="left")
D["model"] = D.pt_live + 0.2 * D.tot_tp_10.fillna(0)
D["edge"] = D.model - D.open_total
B = D[D.edge.abs() >= 3].copy(); sg = np.sign(B.edge)
B["res"] = sg * (B.pts - B.open_total); B = B[B.res != 0]; sg = np.sign(B.edge)
B["won"] = B.res > 0; B["side"] = np.where(B.edge > 0, "over", "under")
B["clv"] = sg * (B.close_t - B.open_total)
B["inj_open"] = (B.home_miss_off_open + B.away_miss_off_open) - (B.home_miss_def_open + B.away_miss_def_open)   # + = offense missing (lower total)
B["news"] = sg * -(((B.home_miss_off - B.home_miss_off_open) + (B.away_miss_off - B.away_miss_off_open)) - ((B.home_miss_def - B.home_miss_def_open) + (B.away_miss_def - B.away_miss_def_open)))
B["luck"] = sg * -B.L_total; B["form"] = sg * B.tot_tp_10
B["b2b"] = B.b2b_home.astype(float) + B.b2b_away.astype(float)
B["month"] = pd.to_datetime(B.date).dt.month
B["pace"] = B.open_total
B.to_csv(os.path.join(W, "analysis", "total_autopsy_bets.csv"), index=False)
w, l = B[B.won], B[~B.won]
print(f"{len(B)} totals bets: {len(w)} won ({len(w) / len(B):.1%})\nWINS vs LOSSES averages:")
for c, lab in (("edge", "edge (signed)"), ("pace", "opening total"), ("clv", "line move our way (pts)"), ("inj_open", "offense missing at open"),
               ("news", "injury news after open (+ = helped us)"), ("luck", "shooting-luck agrees (+)"), ("form", "form agrees (+)"), ("b2b", "back-to-backs in game")):
    print(f"  {lab:38s} wins {w[c].mean():+8.2f}  losses {l[c].mean():+8.2f}")
def grp(lab, key):
    t = B.groupby(key, observed=True).won.agg(["size", "mean"]); print(f"\n{lab}")
    for k, r in t.iterrows():
        sub = B[np.asarray(key == k) if not isinstance(key, str) else B[key] == k]
        per = " ".join(f"{s}:{(lambda x: f'{x.won.sum() * 100 / 110 - (~x.won).sum():+.0f}')(sub[sub.season == s])}" for s in SEAS)
        print(f"  {str(k):26s} {int(r['size']):4d} bets  won {r['mean']:.1%}  {r['mean'] * r['size'] * 100 / 110 - (1 - r['mean']) * r['size']:+6.1f}u   [{per}]")
grp("Over or under", B.side)
grp("Edge size", pd.cut(B.edge.abs(), [3, 4, 5, 7, 30]))
grp("Opening total", pd.cut(B.pace, [0, 215, 225, 235, 400]))
grp("Side x total level", B.side + " " + pd.cut(B.pace, [0, 220, 232, 400], labels=["low", "mid", "high"]).astype(str))
grp("Line move", pd.cut(B.clv, [-30, -0.75, 0.25, 30], labels=["against", "none", "our way"]))
grp("Injury news after open", pd.cut(B.news, [-30, -0.3, 0.3, 30], labels=["hurt us", "none", "helped us"]))
grp("Back-to-backs", B.b2b)
grp("Shooting luck", pd.cut(B.luck, [-99, -3, 3, 99], labels=["against us", "neutral", "with us"]))
grp("Month", B.month)
grp("Side x half of season", B.side + " " + np.where(B.month.isin([2, 3, 4]), "Feb-Apr", "Oct-Jan"))
