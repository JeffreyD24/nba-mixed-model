"""NFL autopsy: full-game spread and total bets at the opener (edge 3+, early-week model like the live alerts), 2020-2025
seasons. Openers: DraftKings from the odds history (2020-23), the backtest opener (2024-25). Wins vs losses by group.
  python analysis/nfl_autopsy.py WORKDIR NFL_REPO"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
P = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(N, "backtests", "predictions_20*.csv")))])
P = P[P.season >= 2020].copy(); P["date"] = pd.to_datetime(P.date).dt.strftime("%Y-%m-%d")
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nfl_open_close.csv")); O = O[O.book == "draftkings"]
P = P.merge(O[["date", "home", "away", "open_spread", "open_total", "close_spread", "close_total"]].add_prefix("dk_").rename(
    columns={"dk_date": "date", "dk_home": "home", "dk_away": "away"}), on=["date", "home", "away"], how="left")
P["o_sp"] = P.dk_open_spread.combine_first(P.open_spread); P["o_tot"] = P.dk_open_total.combine_first(P.open_total)
P["c_sp"] = P.spread; P["c_tot"] = P.total
P["pm"] = P.pred_margin_early.combine_first(P.pred_margin); P["pt"] = P.pred_total_early.combine_first(P.pred_total)
P = P.dropna(subset=["o_sp", "o_tot", "pm"])
print("games with an opener by season:", P.groupby("season").size().to_dict())
P["margin"] = P.home_pts - P.away_pts; P["tp"] = P.home_pts + P.away_pts
def u(s): w, l = (s.res > 0).sum(), (s.res < 0).sum(); return w, l, w * 100 / 110 - l
def grp(B, lab, key):
    print(f"\n{lab}")
    for k, g in B.groupby(key, observed=True):
        w, l, uu = u(g); per = " ".join(f"{s}:{u(g[g.season == s])[2]:+.0f}" for s in sorted(B.season.unique()))
        print(f"  {str(k):26s} {w + l:4d} bets  won {w / max(w + l, 1):.1%}  {uu:+6.1f}u   [{per}]")
# spreads
e = P.pm + P.o_sp; B = P[e.abs() >= 3].copy(); sg = np.sign(e[e.abs() >= 3])
B["res"] = sg * (B.margin + B.o_sp); B["side"] = np.where(sg > 0, "home", "away")
B["line_us"] = sg * B.o_sp; B["dog"] = B.line_us > 0; B["clv"] = sg * (B.o_sp - B.c_sp)
B["qb_out"] = np.where(sg > 0, B.home_qb_miss_early, B.away_qb_miss_early).astype(float) if "home_qb_miss_early" in B else 0
B["opp_qb_out"] = np.where(sg > 0, B.away_qb_miss_early, B.home_qb_miss_early).astype(float)
B["inj_edge"] = sg * ((B.away_miss_off_early.fillna(0) + B.home_miss_def_early.fillna(0)) - (B.home_miss_off_early.fillna(0) + B.away_miss_def_early.fillna(0)))
w, l, uu = u(B); print(f"\nSPREADS: {w + l} bets, {w / (w + l):.1%}, {uu:+.1f}u")
grp(B, "Season", "season"); grp(B, "Side", "side"); grp(B, "Fav/dog", np.where(B.dog, "dog", "fav"))
grp(B, "Side x fav/dog", B.side + " " + np.where(B.dog, "dog", "fav"))
grp(B, "Spread we bet", pd.cut(B.line_us, [-30, -7.5, -3.5, -0.5, 3.5, 7.5, 30]))
grp(B, "Edge size", pd.cut(sg * (B.pm + B.o_sp), [3, 4, 5, 7, 40]))
grp(B, "Week", pd.cut(B.week, [0, 4, 9, 14, 22], labels=["1-4", "5-9", "10-14", "15+"]))
grp(B, "Line move", pd.cut(B.clv, [-30, -0.25, 0.25, 30], labels=["against", "none", "our way"]))
grp(B, "Our QB out (early report)", B.qb_out > 0); grp(B, "Their QB out", B.opp_qb_out > 0)
grp(B, "Injury edge (EPM-style value)", pd.cut(B.inj_edge, [-50, -0.5, 0.5, 50], labels=["injuries vs us", "even", "injuries for us"]))
grp(B, "Rest", np.where(B.bye_home.astype(bool) | B.bye_away.astype(bool), "a team off a bye", np.where(B.short_home.astype(bool) | B.short_away.astype(bool), "short week", "normal")))
grp(B, "Divisional/neutral/indoor", np.where(B.neutral.astype(bool), "neutral", np.where(B.indoor.astype(bool), "indoor", "outdoor")))
# totals
e = P.pt - P.o_tot; B = P[e.abs() >= 3].copy(); sg = np.sign(e[e.abs() >= 3])
B["res"] = sg * (B.tp - B.o_tot); B["side"] = np.where(sg > 0, "over", "under"); B["clv"] = sg * (B.c_tot - B.o_tot)
w, l, uu = u(B); print(f"\nTOTALS: {w + l} bets, {w / (w + l):.1%}, {uu:+.1f}u")
grp(B, "Season", "season"); grp(B, "Side", "side"); grp(B, "Total level", pd.cut(B.o_tot, [0, 40, 44, 48, 80]))
grp(B, "Side x level", B.side + " " + pd.cut(B.o_tot, [0, 42, 47, 80], labels=["low", "mid", "high"]).astype(str))
grp(B, "Edge size", pd.cut(sg * (B.pt - B.o_tot), [3, 4, 5, 7, 40]))
grp(B, "Week", pd.cut(B.week, [0, 4, 9, 14, 22], labels=["1-4", "5-9", "10-14", "15+"]))
grp(B, "Line move", pd.cut(B.clv, [-30, -0.25, 0.25, 30], labels=["against", "none", "our way"]))
grp(B, "Indoor/outdoor", np.where(B.indoor.astype(bool), "indoor", "outdoor"))
grp(B, "Side x indoor", B.side + " " + np.where(B.indoor.astype(bool), "indoor", "outdoor"))
