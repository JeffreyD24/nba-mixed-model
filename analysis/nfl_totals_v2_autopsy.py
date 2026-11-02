"""NFL totals v2 (live Nov 2, 2026): average of (team model + weather, week 15+ shrink) and (player model + weather), edge 2+,
weeks 5-14, graded at DK openers 2020-2025. Wins vs losses by every trait we have.
  python analysis/nfl_totals_v2_autopsy.py WORKDIR NFL_REPO"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
exec(open(os.path.join(W, "analysis", "nfl_totals_autopsy.py")).read().split("B = P[e.abs() >= 3]")[0].split('N = os.path.abspath(sys.argv[2])', 1)[1])
PM = pd.read_csv(os.path.join(W, "analysis", "nfl_player_model_preds.csv"))
keep = ["date", "home", "away", "A_t", "h_qb_epa", "a_qb_epa", "h_pass_def", "a_pass_def", "h_plays", "a_plays", "h_qb_change", "a_qb_change", "h_n_prev", "a_n_prev"]
P = P.merge(PM[keep], on=["date", "home", "away"], how="left")
P["blend"] = (P.pt_adj + P.A_t) / 2; e = P.blend - P.o_tot
m = (e.abs() >= 2) & P.week.between(5, 14) & P.A_t.notna()
B = P[m].copy(); sg = np.sign(e[m]); B["sg"] = sg; B["edge"] = sg * e[m]
B["res"] = sg * (B.tp - B.o_tot); B["side"] = np.where(sg > 0, "over", "under"); B["clv"] = sg * (B.c_tot - B.o_tot); B["won"] = B.res > 0
V2 = V[["date", "home", "away", "temp", "wind", "roof", "surface", "gametime", "weekday", "home_rest", "away_rest", "overtime", "spread_line"]]
B = B.drop(columns=[c for c in V2.columns if c in B and c not in ("date", "home", "away")]).merge(V2, on=["date", "home", "away"], how="left")
B["team_e"] = sg * (B.pt_adj - B.o_tot); B["play_e"] = sg * (B.A_t - B.o_tot)      # each model's edge on our side
B["agree"] = np.where((B.team_e > 0) & (B.play_e > 0), "both models past the line", np.where(B.team_e > 0, "only team model", "only player model"))
B["both2"] = np.where((B.team_e >= 2) & (B.play_e >= 2), "both 2+", "not both 2+")
B["outdoor_g"] = np.where(B.roof.isin(["outdoors", "open"]), "outdoor", "indoor")
B["slot"] = np.where(B.weekday.isin(["Thursday", "Monday"]) | (B.gametime >= "19:00"), "primetime", np.where(B.gametime >= "15:30", "late afternoon", "early"))
B["qb_sum"] = B.h_qb_epa + B.a_qb_epa; B["fav"] = B.o_sp.abs()
B.to_csv(os.path.join(W, "analysis", "nfl_totals_v2_bets.csv"), index=False)
def u(s): w, l = (s.res > 0).sum(), (s.res < 0).sum(); return w, l, w * 100 / 110 - l
def grp(lab, key):
    print(f"\n{lab}")
    for k, g in B.groupby(key, observed=True):
        w, l, uu = u(g); per = " ".join(f"{s % 100}:{u(g[g.season == s])[2]:+.0f}" for s in SEAS)
        print(f"  {str(k):28s} {w + l:4d} bets  won {w / max(w + l, 1):.1%}  {uu:+6.1f}u   [{per}]")
w, l, uu = u(B); print(f"NFL TOTALS v2: {w + l} bets, {w / (w + l):.1%}, {uu:+.1f}u")
grp("Season", "season"); grp("Side", "side"); grp("Side x indoor/outdoor", B.side + " " + B.outdoor_g)
grp("Which models are past the line", "agree"); grp("Both models 2+ on their own", "both2")
grp("Side x model agreement", B.side + " " + B.agree.str.split().str[0])
grp("Edge size", pd.cut(B.edge, [2, 2.5, 3, 4, 6, 40]))
grp("Week", pd.cut(B.week, [4, 7, 10, 14], labels=["5-7", "8-10", "11-14"]))
grp("Opening total", pd.cut(B.o_tot, [0, 40, 43, 46, 49, 80]))
grp("Side x total level", B.side + " " + pd.cut(B.o_tot, [0, 42, 47, 80], labels=["low <=42", "mid 42.5-47", "high 47.5+"]).astype(str))
grp("Wind", np.where(B.outdoor_g == "indoor", "indoor", pd.cut(B.wind.fillna(-1), [-2, -0.5, 7, 12, 50], labels=["no wind data", "0-7 mph", "8-12", "13+"]).astype(str)))
grp("Side x wind 10+", B.side + " " + np.where((B.outdoor_g == "outdoor") & (B.wind.fillna(0) >= 10), "wind 10+", "calm/indoor"))
grp("Temperature", np.where(B.outdoor_g == "indoor", "indoor", pd.cut(B.temp.fillna(60), [-30, 40, 55, 70, 120], labels=["<=40F", "41-55", "56-70", "71+"]).astype(str)))
grp("Point spread (favorite by)", pd.cut(B.fav, [-0.1, 3, 6.5, 30], labels=["0-3", "3.5-6.5", "7+"]))
grp("Side x spread", B.side + " " + pd.cut(B.fav, [-0.1, 6.5, 30], labels=["close game", "7+ favorite"]).astype(str))
grp("QBs' combined efficiency", pd.qcut(B.qb_sum, 3, labels=["two weak QBs", "middle", "two strong QBs"]))
grp("Side x QBs", B.side + " " + pd.qcut(B.qb_sum, 3, labels=["weak QBs", "mid", "strong QBs"]).astype(str))
grp("A starting QB changed recently", np.where((B.h_qb_change + B.a_qb_change) > 0, "new starter", "same starters"))
grp("QB ruled out (early injury report)", np.where((B.home_qb_miss_early.fillna(0) + B.away_qb_miss_early.fillna(0)) > 0, "a QB out", "none"))
grp("Line move by close", pd.cut(B.clv, [-30, -0.25, 0.25, 30], labels=["moved against us", "no move", "moved our way"]))
grp("Kickoff slot", "slot"); grp("Divisional game", B.div_game.map({1: "divisional", 0: "non-div"}))
grp("Rest", np.where((B.home_rest >= 10) | (B.away_rest >= 10), "a team off a bye", np.where((B.home_rest <= 5) | (B.away_rest <= 5), "short week", "normal")))
grp("Pace", pd.qcut(B.h_plays + B.a_plays, 3, labels=["slow", "average", "fast"]))
grp("Overtime", B.overtime.map({1: "went to OT", 0: "no OT"}))
print("\nmargins: won median", np.median(B[B.won].res), "| lost median", np.median(B[~B.won & (B.res < 0)].res),
      "| lost by 3 or less:", int(((B.res < 0) & (B.res >= -3)).sum()), "| won by 3 or less:", int(((B.res > 0) & (B.res <= 3)).sum()))
