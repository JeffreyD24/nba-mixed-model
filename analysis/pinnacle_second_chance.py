"""NBA: wait for Pinnacle? For each game, the DraftKings line at the moment Pinnacle first posts, and Pinnacle's first line.
  A = bet at DK's opener (current), B = bet at DK when Pinnacle posts, only if Pinnacle agrees or matches,
  C = second-chance bets: no bet at the opener, but edge 3+ vs DK's line when Pinnacle posts AND Pinnacle agrees.
Totals: live model (luck + form). Spreads: live spread model (roster + form), Oct-Jan only, no home underdogs.
  python analysis/pinnacle_second_chance.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.argv = ["x", W]
exec(open(os.path.join(W, "analysis", "form_adjust.py")).read().split("rows = []\nfor mk")[0])
R = pd.read_csv(os.path.join(W, "analysis", "roster_strength.csv"))
for side in ("home", "away"):
    P = P.merge(R[["date", "team", "delta"]].rename(columns={"team": side, "delta": f"{side}_rd"}), on=["date", side], how="left")
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_snapshots.csv.gz"), parse_dates=["t"])
pin = O[O.book == "pinnacle"].dropna(subset=["sp", "tot"]).sort_values("t").groupby(["date", "home", "away"]).head(1)[["date", "home", "away", "t", "sp", "tot"]].rename(columns={"t": "t_pin", "sp": "pin_sp", "tot": "pin_tot"})
dk = O[O.book == "draftkings"].dropna(subset=["sp", "tot"]).sort_values("t")
d0 = dk.groupby(["date", "home", "away"]).head(1)[["date", "home", "away", "sp", "tot"]].rename(columns={"sp": "dk_o_sp", "tot": "dk_o_tot"})
dp = dk.merge(pin[["date", "home", "away", "t_pin"]], on=["date", "home", "away"])
dp = dp[dp.t <= dp.t_pin].groupby(["date", "home", "away"]).tail(1)[["date", "home", "away", "sp", "tot"]].rename(columns={"sp": "dk_p_sp", "tot": "dk_p_tot"})
G = P.merge(d0, on=["date", "home", "away"]).merge(pin, on=["date", "home", "away"]).merge(dp, on=["date", "home", "away"])
G["tot_m"] = G.pt_live + 0.20 * G.tot_tp_10.fillna(0)
G["sp_m"] = G.pred_margin + 0.11 * G.sp_mg_10.fillna(0) + 0.57 * (G.home_rd - G.away_rd).fillna(0)
G["early"] = pd.to_datetime(G.date).dt.month.isin([10, 11, 12, 1])
def s_(r): w, l = (r > 0).sum(), (r < 0).sum(); return f"{w + l:4d} {w / max(w + l, 1):.1%} {w * 100 / 110 - l:+6.1f}u"
for mk in ("tot", "sp"):
    if mk == "tot":
        e0 = G.tot_m - G.dk_o_tot; r0 = np.sign(e0) * (G.pts - G.dk_o_tot)
        e1 = G.tot_m - G.dk_p_tot; r1 = np.sign(e1) * (G.pts - G.dk_p_tot)
        agree = np.sign(G.pin_tot - G.dk_p_tot) * np.sign(e1) >= 0      # Pinnacle at or beyond DK's number toward our side
        ok = pd.Series(True, index=G.index)
    else:
        e0 = G.sp_m + G.dk_o_sp; r0 = np.sign(e0) * (G.margin + G.dk_o_sp)
        e1 = G.sp_m + G.dk_p_sp; r1 = np.sign(e1) * (G.margin + G.dk_p_sp)
        agree = np.sign(G.dk_p_sp - G.pin_sp) * np.sign(e1) >= 0
        ok = G.early & ~((e0 > 0) & (G.dk_o_sp > 0))
    bet0 = (e0.abs() >= 3) & ok; bet1 = (e1.abs() >= 3) & ok
    print(f"\n{'TOTALS' if mk == 'tot' else 'SPREADS (Oct-Jan, no home dogs)'}: hours from DK open to Pinnacle open, median {((G.t_pin - G.t_pin.min()).dt.total_seconds() * 0).median():.0f}")
    for s in SEAS:
        k = G.season == s
        print(f"  {s}: A at DK open {s_(r0[bet0 & k])} | B wait, Pinnacle agrees {s_(r1[bet1 & agree & k])} | C second chance {s_(r1[~bet0 & bet1 & agree & k])}")
    print(f"  all : A {s_(r0[bet0])} | B {s_(r1[bet1 & agree])} | C {s_(r1[~bet0 & bet1 & agree])} | A+C {s_(pd.concat([r0[bet0], r1[~bet0 & bet1 & agree]]))}")
