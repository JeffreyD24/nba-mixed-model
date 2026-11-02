"""NBA spreads: why does the model win Oct-Jan and lose Feb-Apr? 2023-24..2025-26, DraftKings openers, model = roster + form
(the live spread model). Compares the two halves on the games themselves and on how the market (sharps) moved.
  python analysis/half_compare.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.argv = ["x", W]
exec(open(os.path.join(W, "analysis", "form_adjust.py")).read().split("rows = []\nfor mk")[0])
R = pd.read_csv(os.path.join(W, "analysis", "roster_strength.csv"))
for side in ("home", "away"):
    P = P.merge(R[["date", "team", "delta", "n_rot"]].rename(columns={"team": side, "delta": f"{side}_rd", "n_rot": f"{side}_nrot"}), on=["date", side], how="left")
OC = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"))
dk = OC[OC.book == "draftkings"][["date", "home", "away", "open_spread", "close_spread"]].rename(columns={"open_spread": "dk_o", "close_spread": "dk_c"})
pn = OC[OC.book == "pinnacle"][["date", "home", "away", "open_spread", "close_spread"]].rename(columns={"open_spread": "pin_o", "close_spread": "pin_c"})
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
inj = ["home_miss_off", "home_miss_def", "away_miss_off", "away_miss_def", "home_miss_off_open", "home_miss_def_open", "away_miss_off_open",
       "away_miss_def_open", "home_n_out", "away_n_out", "home_n_out_open", "away_n_out_open"]
G = P.drop(columns=[c for c in P if c in inj]).merge(dk, on=["date", "home", "away"]).merge(pn, on=["date", "home", "away"], how="left").merge(T[["date", "home", "away"] + inj], on=["date", "home", "away"], how="left")
# season-to-date win % (tanking / playoff race proxy)
rows = []
for r in T.sort_values("date").itertuples():
    rows += [dict(season=r.season, date=r.date, team=r.home, w=int(r.home_pts > r.away_pts)), dict(season=r.season, date=r.date, team=r.away, w=int(r.away_pts > r.home_pts))]
Lw = pd.DataFrame(rows).sort_values(["season", "team", "date"]); Lw["wpct"] = Lw.groupby(["season", "team"]).w.transform(lambda v: v.shift().expanding().mean())
wp = Lw.set_index(["date", "team"]).wpct
G["h_wp"] = [wp.get((d, t), np.nan) for d, t in zip(G.date, G.home)]; G["a_wp"] = [wp.get((d, t), np.nan) for d, t in zip(G.date, G.away)]
G["sp_model"] = G.pred_margin + 0.11 * G.sp_mg_10.fillna(0) + 0.57 * (G.home_rd - G.away_rd).fillna(0)
G["e"] = G.sp_model + G.dk_o
B = G[G.e.abs() >= 3].copy(); sg = np.sign(B.e)
B["res"] = sg * (B.margin + B.dk_o); B = B[B.res != 0]; sg = np.sign(B.e)
B["won"] = B.res > 0
B["late"] = pd.to_datetime(B.date).dt.month.isin([2, 3, 4]); B["half"] = np.where(B.late, "Feb-Apr", "Oct-Jan")
B["home_bet"] = sg > 0; B["our_line"] = sg * B.dk_o; B["dog"] = B.our_line > 0
B["our_wp"] = np.where(B.home_bet, B.h_wp, B.a_wp); B["opp_wp"] = np.where(B.home_bet, B.a_wp, B.h_wp)
B["dk_move"] = sg * (B.dk_o - B.dk_c)                # + = DK's line moved toward our side
B["pin_open_vs_dk"] = sg * (B.dk_o - B.pin_o)          # + = Pinnacle opened more on our side than DK
B["pin_move"] = sg * (B.pin_o - B.pin_c)               # + = Pinnacle moved toward us
B["close_vs_model"] = sg * (B.sp_model + B.pin_c.fillna(B.dk_c))      # our edge left vs the sharp close
# injuries: value out at open and news after the open, our side vs theirs
def side(hc, ac): return np.where(B.home_bet, B[hc] - B[ac], B[ac] - B[hc])
B["our_out_open"] = np.where(B.home_bet, B.home_n_out_open, B.away_n_out_open); B["opp_out_open"] = np.where(B.home_bet, B.away_n_out_open, B.home_n_out_open)
B["our_out_final"] = np.where(B.home_bet, B.home_n_out, B.away_n_out); B["opp_out_final"] = np.where(B.home_bet, B.away_n_out, B.home_n_out)
B["late_scratches_us"] = B.our_out_final - B.our_out_open; B["late_scratches_them"] = B.opp_out_final - B.opp_out_open
val = lambda pfx: (B[f"{pfx}_miss_off"] + B[f"{pfx}_miss_def"]) - (B[f"{pfx}_miss_off_open"] + B[f"{pfx}_miss_def_open"])
B["news_val_us"] = np.where(B.home_bet, val("home"), val("away")); B["news_val_them"] = np.where(B.home_bet, val("away"), val("home"))
B["roster_us"] = sg * (B.home_rd - B.away_rd)
def s_(g): w = g.won.sum(); n = len(g); return f"{n:4d} {w / n:.1%} {w * 100 / 110 - (n - w):+6.1f}u"
print(f"{len(B)} spread bets (roster + form model, DK openers, edge 3+)")
for h, g in B.groupby("half"): print(f"  {h}: {s_(g)}  by season " + " ".join(f"{s}: {s_(g[g.season == s])}" for s in SEAS))
print("\nTHE TWO HALVES, averages over our bets (Oct-Jan | Feb-Apr):")
for c, lab in (("our_line", "points we get (+ = underdog)"), ("dog", "share underdogs"), ("home_bet", "share home"), ("our_wp", "our team's win %"),
               ("opp_wp", "opponent's win %"), ("our_out_open", "our players out at open"), ("opp_out_open", "their players out at open"),
               ("late_scratches_us", "OUR players ruled out after the open"), ("late_scratches_them", "THEIR players ruled out after the open"),
               ("news_val_us", "value lost by us after open (EPM)"), ("news_val_them", "value lost by them after open"),
               ("roster_us", "roster change (ours - theirs)"), ("dk_move", "DK line move toward us (pts)"), ("pin_open_vs_dk", "Pinnacle opener vs DK (toward us)"),
               ("pin_move", "Pinnacle move toward us (pts)"), ("close_vs_model", "our edge vs the sharp close (pts)")):
    a, b_ = B[~B.late][c].astype(float).mean(), B[B.late][c].astype(float).mean()
    print(f"  {lab:40s} {a:+7.2f} | {b_:+7.2f}")
print("\nWIN RATE by market move, each half (does the market already know when we're wrong?)")
for h, g in B.groupby("half"):
    for lab, k in (("Pinnacle moved against us 1+", g.pin_move <= -1), ("Pinnacle moved against <1", (g.pin_move < 0) & (g.pin_move > -1)),
                   ("no Pinnacle move", g.pin_move == 0), ("Pinnacle moved toward us", g.pin_move > 0)):
        print(f"  {h} {lab:30s} {s_(g[k])}")
print("\nWIN RATE by late scratches (players ruled out AFTER the opener)")
for h, g in B.groupby("half"):
    for lab, k in (("we lost a player late", g.late_scratches_us > 0), ("they lost a player late", g.late_scratches_them > 0), ("no late scratches", (g.late_scratches_us <= 0) & (g.late_scratches_them <= 0))):
        print(f"  {h} {lab:30s} {s_(g[k])}")
print("\nWIN RATE by team quality (tanking / resting)")
B["matchup"] = np.where(B.our_wp < 0.4, "we bet a bad team (<40%)", np.where(B.our_wp > 0.6, "we bet a good team (>60%)", "we bet a middling team"))
for h, g in B.groupby("half"):
    for k, gg in g.groupby("matchup"): print(f"  {h} {k:30s} {s_(gg)}")
    for lab, k in (("opponent is bad (<40%)", g.opp_wp < 0.4), ("opponent is good (>60%)", g.opp_wp > 0.6)): print(f"  {h} {lab:30s} {s_(g[k])}")
print("\nHow often games change after the open (all games, not just bets), per game:")
G["late"] = pd.to_datetime(G.date).dt.month.isin([2, 3, 4])
G["late_outs"] = (G.home_n_out - G.home_n_out_open) .clip(lower=0) + (G.away_n_out - G.away_n_out_open).clip(lower=0)
G["abs_move"] = (G.pin_c.fillna(G.dk_c) - G.dk_o).abs()
for h, g in G.groupby("late"): print(f"  {'Feb-Apr' if h else 'Oct-Jan'}: players ruled out after the open {g.late_outs.mean():.2f} per game; "
                                   f"average line move open->close {g.abs_move.mean():.2f} pts; moves of 2+ pts {(g.abs_move >= 2).mean():.0%}")
B.to_csv(os.path.join(W, "analysis", "half_compare_bets.csv"), index=False)
