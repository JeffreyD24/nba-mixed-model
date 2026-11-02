"""NFL totals with weather (the test-tracked rule: early-week model total, wind and cold adjustment, week 15+ shrink toward the
line; weights fit leaving the test season out), graded at DK openers 2020-2025, edge 3+. Wins vs losses by every trait we have.
  python analysis/nfl_totals_autopsy.py WORKDIR NFL_REPO"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
src = open(os.path.join(W, "analysis", "nfl_fixes.py")).read().split('print("seasons", SEAS)')[0].split("W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])", 1)[1]
exec(src)
P = P.drop_duplicates(["date", "home", "away"]).reset_index(drop=True)   # a few games had two DK opener rows
# rebuild the weather + late-shrink totals prediction exactly like run("tot", ["wind_x","cold_x"], True)
base, y, line = P.pt, P.tp, P.o_tot; adj = base.copy()
for s in SEAS:
    te = P.season == s; tr = ~te; feats = ["wind_x", "cold_x"]
    b = np.linalg.lstsq(P.loc[tr, feats].values, (y - base)[tr].values, rcond=None)[0]; a = base[te] + P.loc[te, feats].values @ b
    k_tr = tr & (P.late == 1); d_ = base[k_tr] - line[k_tr]; r_ = y[k_tr] - line[k_tr]; c = float((d_ * r_).sum() / (d_ * d_).sum())
    lt = te & (P.late == 1); a[lt] = line[lt] + c * (a[lt] - line[lt]); adj[te] = a
P["pt_adj"] = adj; e = P.pt_adj - P.o_tot
B = P[e.abs() >= 3].copy(); sg = np.sign(e[e.abs() >= 3]); B["edge"] = sg * e[e.abs() >= 3]
B["res"] = sg * (B.tp - B.o_tot); B["side"] = np.where(sg > 0, "over", "under"); B["clv"] = sg * (B.c_tot - B.o_tot)
B["won"] = B.res > 0
# extra traits
V2 = V[["date", "home", "away", "temp", "wind", "roof", "surface", "gametime", "weekday", "home_rest", "away_rest", "overtime"]]
B = B.drop(columns=[c for c in V2.columns if c in B and c not in ("date","home","away")]).merge(V2, on=["date", "home", "away"], how="left")
PM = pd.read_csv(os.path.join(W, "analysis", "nfl_player_model_preds.csv"))[["date", "home", "away", "A_t", "pace", "qbchg_s", "pass_sum", "h_qb_change", "a_qb_change"]]
B = B.merge(PM, on=["date", "home", "away"], how="left")
B["player_agrees"] = np.where(B.A_t.isna(), "n/a", np.where(np.sign(B.A_t - B.o_tot) == np.where(B.side == "over", 1, -1), "agrees", "disagrees"))
B["slot"] = np.where(B.weekday.isin(["Thursday", "Monday"]) | (B.gametime >= "19:00"), "primetime", np.where(B.gametime >= "15:30", "late afternoon", "early"))
B["outdoor_g"] = np.where(B.roof.isin(["outdoors", "open"]), "outdoor", "indoor")
B["miss"] = B.tp - B.o_tot     # points above (+) / below (-) the opener
B.to_csv(os.path.join(W, "analysis", "nfl_totals_autopsy_bets.csv"), index=False)
def u(s): w, l = (s.res > 0).sum(), (s.res < 0).sum(); return w, l, w * 100 / 110 - l
def grp(lab, key):
    print(f"\n{lab}")
    for k, g in B.groupby(key, observed=True):
        w, l, uu = u(g); per = " ".join(f"{s % 100}:{u(g[g.season == s])[2]:+.0f}" for s in SEAS)
        print(f"  {str(k):28s} {w + l:4d} bets  won {w / max(w + l, 1):.1%}  {uu:+6.1f}u   [{per}]")
w, l, uu = u(B); print(f"TOTALS + WEATHER + LATE SHRINK: {w + l} bets, {w / (w + l):.1%}, {uu:+.1f}u")
grp("Season", "season"); grp("Side", "side"); grp("Side x indoor/outdoor", B.side + " " + B.outdoor_g)
grp("Wind (outdoor games)", np.where(B.outdoor_g == "indoor", "indoor", pd.cut(B.wind.fillna(-1), [-2, -0.5, 5, 10, 15, 50], labels=["outdoor, no wind data", "0-5 mph", "6-10", "11-15", "16+"]).astype(str)))
grp("Side x wind", B.side + " " + np.where(B.outdoor_g == "indoor", "indoor", np.where(B.wind.fillna(0) >= 11, "wind 11+", "wind <11")))
grp("Temperature (outdoor)", np.where(B.outdoor_g == "indoor", "indoor", pd.cut(B.temp.fillna(60), [-30, 32, 45, 60, 75, 120], labels=["<=32F", "33-45", "46-60", "61-75", "76+"]).astype(str)))
grp("Side x cold", B.side + " " + np.where(B.outdoor_g == "indoor", "indoor", np.where(B.temp.fillna(60) <= 40, "40F or colder", "warmer")))
grp("Opening total", pd.cut(B.o_tot, [0, 40, 43, 46, 49, 80])); grp("Side x total level", B.side + " " + pd.cut(B.o_tot, [0, 42, 47, 80], labels=["low <=42", "mid 42.5-47", "high 47.5+"]).astype(str))
grp("Edge size", pd.cut(B.edge, [3, 4, 5, 7, 40])); grp("Week", pd.cut(B.week, [0, 4, 9, 14, 22], labels=["1-4", "5-9", "10-14", "15+"]))
grp("Side x week", B.side + " " + pd.cut(B.week, [0, 8, 22], labels=["wk 1-8", "wk 9+"]).astype(str))
grp("Line move by close", pd.cut(B.clv, [-30, -0.25, 0.25, 30], labels=["moved against us", "no move", "moved our way"]))
grp("Kickoff slot", "slot"); grp("Divisional game", B.div_game.map({1: "divisional", 0: "non-div"}))
grp("Surface", B.surface.fillna("?").str.contains("grass").map({True: "grass", False: "turf"}))
grp("Rest", np.where((B.home_rest >= 10) | (B.away_rest >= 10), "a team off a bye", np.where((B.home_rest <= 5) | (B.away_rest <= 5), "short week", "normal")))
grp("Player model (QB/defense EPA) agrees?", "player_agrees")
grp("Side x player model", B.side + " " + B.player_agrees)
grp("A starting QB changed", np.where(B.qbchg_s.fillna(0) > 0, "new starter", "same starters"))
grp("Pace (both teams' plays/game)", pd.cut(B.pace, [0, 124, 128, 200], labels=["slow", "average", "fast"]))
grp("Overtime", B.overtime.map({1: "went to OT", 0: "no OT"}))
print("\nHow far the losers missed vs the winners (points vs the opener, from our side):")
for k, g in B.groupby("won"): print(f"  {'won' if k else 'lost':5s} median {np.median(g.res):+.1f}  |  lost by 3 or less: {((g.res < 0) & (g.res >= -3)).sum()}")
