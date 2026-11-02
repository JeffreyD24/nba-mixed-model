"""Why do NBA spread bets lose? Every Model 1 spread bet at the opener (edge 3+), 2023-24 (DraftKings openers), 2024-25 and
2025-26: wins vs losses compared on everything known about the game, then win rate by group.
  python analysis/spread_autopsy.py WORKDIR -> analysis/spread_autopsy_bets.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
sys.argv = ["x", W]
exec(open(os.path.join(W, "analysis", "form_adjust.py")).read().split("rows = []\nfor mk")[0])    # P with form, luck
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
inj = ["home_miss_off", "home_miss_def", "home_n_out", "away_miss_off", "away_miss_def", "away_n_out",
       "home_miss_off_open", "home_miss_def_open", "home_n_out_open", "away_miss_off_open", "away_miss_def_open", "away_n_out_open", "spread", "total"]
D = P.merge(T[["date", "home", "away"] + inj], on=["date", "home", "away"], how="left", suffixes=("", "_t"))
P2 = pd.read_csv(os.path.join(W, "_tmp", "test_2024_games.csv"))[["date", "home", "away", "sp_close", "b2b_home", "b2b_away"]]
P1 = pd.read_csv(os.path.join(W, "_tmp", "model1_open_preds.csv"))[["date", "home", "away", "b2b_home", "b2b_away"]]
P1["date"] = pd.to_datetime(P1.date).dt.strftime("%Y-%m-%d")
D = D.merge(pd.concat([P1, P2[["date", "home", "away", "b2b_home", "b2b_away"]]]), on=["date", "home", "away"], how="left")
D = D.merge(P2[["date", "home", "away", "sp_close"]], on=["date", "home", "away"], how="left")
D["close_sp"] = np.where(D.season == 2024, D.sp_close, D.spread)
# season-to-date team strength
D["edge"] = D.pred_margin + D.open_spread
B = D[D.edge.abs() >= 3].copy()
home = B.edge > 0; sg = np.where(home, 1, -1)
B["side"] = np.where(home, "home", "away")
B["cover"] = sg * (B.margin + B.open_spread)
B = B[B.cover != 0]; home = B.edge > 0; sg = np.where(home, 1, -1)
B["won"] = B.cover > 0
B["our_line"] = sg * B.open_spread                         # + = we got points (underdog)
B["dog"] = B.our_line > 0
B["abs_edge"] = B.edge.abs()
B["clv"] = sg * (B.open_spread - B.close_sp)                # + = line moved our way (pts)
# injuries from our side's view: value missing for us vs for them, at the open, and news after the open
def side_val(c_h, c_a): return np.where(home, B[c_a] - B[c_h], B[c_h] - B[c_a])
B["inj_edge_open"] = np.where(home, (B.away_miss_off_open + B.home_miss_def_open) - (B.home_miss_off_open + B.away_miss_def_open),
                              (B.home_miss_off_open + B.away_miss_def_open) - (B.away_miss_off_open + B.home_miss_def_open))
B["opp_out_open"] = np.where(home, B.away_n_out_open, B.home_n_out_open); B["our_out_open"] = np.where(home, B.home_n_out_open, B.away_n_out_open)
B["news_vs_us"] = np.where(home, (B.home_miss_off - B.home_miss_off_open) - (B.away_miss_off - B.away_miss_off_open),
                           (B.away_miss_off - B.away_miss_off_open) - (B.home_miss_off - B.home_miss_off_open))   # + = more of OUR value went out after the open
B["our_b2b"] = np.where(home, B.b2b_home, B.b2b_away).astype(float); B["opp_b2b"] = np.where(home, B.b2b_away, B.b2b_home).astype(float)
B["our_form"] = sg * B.sp_mg_10                               # + = our team in better recent form than the opponent
B["luck_for_us"] = sg * B.L_margin if "L_margin" in B else np.nan
B["games_in"] = np.minimum(B.h_n, B.a_n)
B["month"] = pd.to_datetime(B.date).dt.month
B["model_mag"] = B.pred_margin.abs(); B["line_mag"] = B.open_spread.abs()
B["model_says_flip"] = np.sign(B.pred_margin) != np.sign(-B.open_spread)   # model picks a different winner than the line
B.to_csv(os.path.join(W, "analysis", "spread_autopsy_bets.csv"), index=False)
w, l = B[B.won], B[~B.won]
print(f"{len(B)} spread bets: {len(w)} won, {len(l)} lost ({len(w) / len(B):.1%})\n")
print("WINS vs LOSSES, averages:")
for c, lab in (("abs_edge", "model edge (pts)"), ("our_line", "our line (+ = getting points)"), ("model_mag", "model margin size"),
               ("line_mag", "spread size"), ("clv", "line move our way by close (pts)"), ("inj_edge_open", "injury value edge at open"),
               ("our_out_open", "our players out at open"), ("opp_out_open", "their players out at open"), ("news_vs_us", "injury news after open vs us"),
               ("our_form", "recent form (ours - theirs)"), ("games_in", "games played (fewer team)"), ("our_b2b", "we're on a back-to-back"),
               ("opp_b2b", "they're on a back-to-back")):
    print(f"  {lab:34s} wins {w[c].mean():+7.2f}   losses {l[c].mean():+7.2f}")

def grp(lab, key):
    t = B.groupby(key, observed=True).won.agg(["size", "mean"])
    print(f"\n{lab}"); [print(f"  {str(k):28s} {int(r['size']):4d} bets  won {r['mean']:.1%}  {r['mean'] * r['size'] * 100 / 110 - (1 - r['mean']) * r['size']:+6.1f}u") for k, r in t.iterrows()]
grp("Side", "side"); grp("Favorite or underdog", np.where(B.dog, "underdog", "favorite"))
grp("Side x fav/dog", B.side + " " + np.where(B.dog, "dog", "fav"))
grp("Spread size we bet", pd.cut(B.our_line, [-30, -7.5, -3.5, 0, 3.5, 7.5, 30]))
grp("Edge size", pd.cut(B.abs_edge, [3, 4, 5, 6, 8, 30]))
grp("Model picks the other team to win outright", B.model_says_flip)
grp("Injury value edge at open (our favor)", pd.cut(B.inj_edge_open, [-20, -0.5, 0.5, 2, 20]))
grp("Their players out at open", pd.cut(B.opp_out_open, [-1, 0, 1, 2, 10]))
grp("Our players out at open", pd.cut(B.our_out_open, [-1, 0, 1, 2, 10]))
grp("Injury news after the open", pd.cut(B.news_vs_us, [-20, -0.3, 0.3, 20], labels=["news helped us", "no news", "news hurt us"]))
grp("Line move open->close", pd.cut(B.clv, [-20, -0.75, 0.25, 20], labels=["moved against", "no move", "moved our way"]))
grp("Recent form", pd.cut(B.our_form, [-50, -3, 3, 50], labels=["we're colder", "similar", "we're hotter"]))
grp("Back-to-backs", np.where(B.our_b2b == 1, "we b2b", "") + np.where(B.opp_b2b == 1, " they b2b", ""))
grp("Month", B.month); grp("Season", B.season)
