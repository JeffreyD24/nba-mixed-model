"""Market blends for the NBA and NFL. For point spreads and totals, blending the model's number with DraftKings' opener
(w x model + (1-w) x line) is exactly the same as requiring a bigger edge (edge x w >= 3), so it's tested as the edge bar, with
w fit leaving the test season out (least squares on the result). Moneylines: tested earlier (nba_moneyline.py; NFL below).
  python analysis/blend_all.py WORKDIR NFL_REPO"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2]); sys.argv = ["x", W]
exec(open(os.path.join(W, "analysis", "validate_dk_2024_26.py")).read().split('print("games at DK lines:"')[0].split('W = os.path.abspath(sys.argv[1]); sys.argv = ["x", W]')[1])
LS = pd.read_csv(os.path.join(W, "analysis", "late_season_games.csv"))[["date", "home", "away", "h_cat", "a_cat", "h_arr", "a_arr"]]
G = G.merge(LS, on=["date", "home", "away"], how="left")
G["tot_model"] = G.tot_model + np.where(G.home.isin(["den", "utah"]), 3.8, 0.0)      # live: altitude
def w_fit(model, line, y, tr):
    d = (model - line)[tr]; r = (y - line)[tr]; return float((d * r).sum() / (d * d).sum())
def sweep(name, model, line, y, sign, rule):
    print(f"\n{name}")
    for lab, mode in (("edge 3+ (current)", ("edge", 3)), ("edge 4+", ("edge", 4)), ("edge 5+", ("edge", 5)), ("blend, blended edge 1.5+", ("blend", 1.5)), ("blend, blended edge 2+", ("blend", 2.0))):
        per = []; tn = tw = 0; ws = []
        for s in SEAS:
            te = (G.season == s).values
            e = sign * (model - line) if False else (model - line)
            if mode[0] == "blend":
                w = w_fit(model, line, y, ~te); ws.append(round(w, 2)); e = w * (model - line)
            k = te & (np.abs(e) >= mode[1]) & rule(e)
            r = np.sign(e[k]) * (y - line)[k]; wn, ln = (r > 0).sum(), (r < 0).sum(); per.append(wn * 100 / 110 - ln); tn += wn + ln; tw += wn
        print(f"  {lab:28s} " + " ".join(f"{x:+6.1f}" for x in per) + f" | {tn:4d} bets {tw / max(tn, 1):.1%} {sum(per):+6.1f}u worst {min(per):+.1f}" + (f"  w={ws}" if ws else ""))
# NBA totals (live): model total vs DK opening total
sweep("NBA TOTALS (live model, DK openers 2023-26)", G.tot_model.values, G.open_tot.values, G.pts.values, 1, lambda e: np.ones(len(e), bool))
# NBA spreads (live rules): home margin model vs -opening spread
late = pd.to_datetime(G.date).dt.month.isin([2, 3, 4]).values
def sp_rule(e):
    home = e > 0; hd = home & (G.open_sp.values > 0)
    trap = np.where(home, G.h_cat == "tanking", G.a_cat == "tanking") | np.where(home, G.a_cat == "middle", G.h_cat == "middle") | (np.where(home, G.h_arr, G.a_arr) > 0)
    return ~hd & (~late | ~trap)
sweep("NBA SPREADS (live rules, DK openers 2023-26)", G.sp_model.values, -G.open_sp.values, G.margin.values, 1, sp_rule)
# ---- NFL (2020-25 openers as in nfl_autopsy.py)
src = open(os.path.join(W, "analysis", "nfl_autopsy.py")).read().split("def u(s)")[0].split("W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])")[1]
ns = {"os": os, "sys": sys, "glob": glob, "np": np, "pd": pd, "W": W, "N": N}; exec(src, ns); NP = ns["P"]
G = NP.reset_index(drop=True); SEAS = sorted(G.season.unique())
sweep("NFL TOTALS (2020-25 openers)", G.pt.values, G.o_tot.values, G.tp.values, 1, lambda e: np.ones(len(e), bool))
sweep("NFL SPREADS (2020-25 openers)", G.pm.values, -G.o_sp.values, G.margin.values, 1, lambda e: np.ones(len(e), bool))
