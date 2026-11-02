"""NBA 2023-24..2025-26 graded at DraftKings' real lines (The Odds API history): opener, +15/30/60 min, close.
Totals: live model (luck + last-10 form). Spreads: test-only model (roster + form). Also the sharp-move model filter on totals
(trained on 2021-22..2023-24 only, tested on 2024-25 and 2025-26).   python analysis/validate_dk_2024_26.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.argv = ["x", W]
exec(open(os.path.join(W, "analysis", "form_adjust.py")).read().split("rows = []\nfor mk")[0])
R = pd.read_csv(os.path.join(W, "analysis", "roster_strength.csv"))
for side in ("home", "away"):
    P = P.merge(R[["date", "team", "delta"]].rename(columns={"team": side, "delta": f"{side}_rd"}), on=["date", side], how="left")
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_snapshots.csv.gz"), parse_dates=["t"])
D = O[O.book == "draftkings"].sort_values("t")
first = D.dropna(subset=["sp", "tot"]).groupby(["date", "home", "away"]).t.min().rename("t0")
D = D.join(first, on=["date", "home", "away"]).dropna(subset=["t0"])
out = {}
for lab, mins in (("open", 0), ("m15", 15), ("m30", 30), ("m60", 60), ("close", None)):
    s = D if mins is None else D[D.t <= D.t0 + pd.Timedelta(minutes=mins)]
    s = s.groupby(["date", "home", "away"]).tail(1).set_index(["date", "home", "away"])[["sp", "tot"]]
    out[lab] = s.add_prefix(f"{lab}_")
K = pd.concat(out.values(), axis=1).reset_index()
G = P.merge(K, on=["date", "home", "away"], how="inner")
G["tot_model"] = G.pt_live + 0.20 * G.tot_tp_10.fillna(0)
G["sp_model"] = G.pred_margin + 0.11 * G.sp_mg_10.fillna(0) + 0.57 * (G.home_rd - G.away_rd).fillna(0)
print("games at DK lines:", G.groupby("season").size().to_dict())
def g_(e, r): m = e.abs() >= 3; rr = np.sign(e[m]) * r[m]; w, l = (rr > 0).sum(), (rr < 0).sum(); return f"{w + l:4d} {w / max(w + l, 1):.1%} {w * 100 / 110 - l:+6.1f}u"
for mk in ("tot", "sp"):
    print(f"\n{'TOTALS (live: luck + form)' if mk == 'tot' else 'SPREADS (test-only: roster + form)'}")
    for s in SEAS:
        d = G[G.season == s]; row = []
        for lab in ("open", "m15", "m30", "m60", "close"):
            ln = d[f"{lab}_{mk}"]
            e = (d.tot_model - ln) if mk == "tot" else (d.sp_model + ln); r = (d.pts - ln) if mk == "tot" else (d.margin + ln)
            row.append(f"{lab}: {g_(e, r)}")
        print(f"  {s}: " + " | ".join(row))
    if mk == "sp":
        for s in SEAS:
            d = G[G.season == s]; e = d.sp_model + d.open_sp; r = d.margin + d.open_sp; late = pd.to_datetime(d.date).dt.month.isin([2, 3, 4])
            hd = (e > 0) & (d.open_sp > 0)
            print(f"  {s} at open: Oct-Jan {g_(e[~late], r[~late])} | Feb-Apr {g_(e[late], r[late])} | Oct-Jan no home dogs {g_(e[~late & ~hd], r[~late & ~hd])}")
# sharp-move model: trained on 2022-24 only (DK open -> Pinnacle close), applied to 2025-26
exec(open(os.path.join(W, "analysis", "sharp_replicate.py")).read().split('print("1. WHAT MOVES')[0].split("W = os.path.abspath(sys.argv[1])")[1].replace("T = pd.read_csv", "T = pd.read_csv", 1))
from sklearn.ensemble import HistGradientBoostingRegressor
feats = OPEN_FEATS["tot"]; Tt = T.dropna(subset=["mv_tot"])
m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=40).fit(Tt[Tt.season <= 2024][feats], Tt[Tt.season <= 2024].mv_tot)
Tt = Tt[Tt.season >= 2025].copy(); Tt["sharp_pred"] = m.predict(Tt[feats])
H = G.merge(Tt[["date", "home", "away", "sharp_pred"]], on=["date", "home", "away"], how="inner")
print(f"\nSharp-move model (trained 2021-24) on 2024-25/2025-26 totals: r with actual move = {np.corrcoef(H.sharp_pred, H.close_tot - H.open_tot)[0, 1]:+.3f}")
for s in (2025, 2026):
    d = H[H.season == s]; e = d.tot_model - d.open_tot; r = d.pts - d.open_tot; ag = np.sign(d.sharp_pred) == np.sign(e)
    print(f"  {s}: all {g_(e, r)} | sharp model agrees {g_(e[ag], r[ag])} | disagrees {g_(e[~ag], r[~ag])}")
