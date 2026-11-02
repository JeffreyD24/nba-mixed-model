"""Can we copy the sharps? The closing line at Pinnacle is the sharp consensus. Two questions, NBA 2021-22..2023-24:
  1. What moves the line from DraftKings' opener to Pinnacle's close (what the sharps react to)?   (descriptive)
  2. A "sharp model": predict that move using only what is known at DraftKings' opener, trained on two seasons and tested
     on the third (all three rotations). Bet DraftKings' opener in the predicted direction; graded on results.
  python analysis/sharp_replicate.py WORKDIR -> analysis/sharp_replicate_games.csv"""
import os, sys
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
W = os.path.abspath(sys.argv[1])
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
OC = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"))
dk = OC[OC.book == "draftkings"][["date", "home", "away", "open_spread", "open_total", "close_spread", "close_total"]].add_prefix("dk_")
pin = OC[OC.book == "pinnacle"][["date", "home", "away", "open_spread", "open_total", "close_spread", "close_total"]].add_prefix("pin_")
dk = dk.rename(columns={"dk_date": "date", "dk_home": "home", "dk_away": "away"}); pin = pin.rename(columns={"pin_date": "date", "pin_home": "home", "pin_away": "away"})
Q = pd.read_csv(os.path.join(W, "analysis", "shot_quality_games.csv"))[["date", "home", "away"] + [c for c in pd.read_csv(os.path.join(W, "analysis", "shot_quality_games.csv"), nrows=1) if c.startswith(("h_pre_", "a_pre_"))] + ["L_total", "L_margin"]]
T = T.merge(dk, on=["date", "home", "away"]).merge(pin, on=["date", "home", "away"], how="left").merge(Q, on=["date", "home", "away"], how="left")
T = T.sort_values("date").reset_index(drop=True)
T["margin"] = T.home_pts - T.away_pts; T["pts"] = T.home_pts + T.away_pts
# season-to-date team form (before each game), rest days
rows = []
for r in T.itertuples():
    for side, team, sgn in (("h", r.home, 1), ("a", r.away, -1)):
        rows.append(dict(i=r.Index, side=side, season=r.season, team=team, date=pd.Timestamp(r.date), mg=sgn * r.margin,
                         pf=r.home_pts if sgn == 1 else r.away_pts, pa=r.away_pts if sgn == 1 else r.home_pts,
                         ats=sgn * (r.margin + r.dk_close_spread), ou=r.pts - r.dk_close_total))
L = pd.DataFrame(rows).sort_values(["season", "team", "date"]); g = L.groupby(["season", "team"])
sh = lambda c, f: g[c].transform(lambda v: f(v.shift()))
L["n"] = g.cumcount(); L["mg_std"] = sh("mg", lambda v: v.expanding().mean()); L["mg10"] = sh("mg", lambda v: v.rolling(10, min_periods=3).mean())
L["pf_std"] = sh("pf", lambda v: v.expanding().mean()); L["pa_std"] = sh("pa", lambda v: v.expanding().mean())
L["ats_std"] = sh("ats", lambda v: v.expanding().mean()); L["ou_std"] = sh("ou", lambda v: v.expanding().mean())
L["ats5"] = sh("ats", lambda v: v.rolling(5, min_periods=3).mean()); L["last_mg"] = g.mg.shift()
L["rest"] = g.date.diff().dt.days.clip(upper=5)
for c in ("n", "mg_std", "mg10", "pf_std", "pa_std", "ats_std", "ou_std", "ats5", "last_mg", "rest"):
    piv = L.pivot_table(index="i", columns="side", values=c)
    T[f"h_{c}"] = piv["h"]; T[f"a_{c}"] = piv["a"]
T["inj_sp_open"] = (T.away_miss_off_open + T.home_miss_def_open) - (T.home_miss_off_open + T.away_miss_def_open)
T["inj_tot_open"] = -(T.home_miss_off_open + T.away_miss_off_open) + (T.home_miss_def_open + T.away_miss_def_open)
T["news_sp"] = ((T.away_miss_off - T.away_miss_off_open) + (T.home_miss_def - T.home_miss_def_open)) - ((T.home_miss_off - T.home_miss_off_open) + (T.away_miss_def - T.away_miss_def_open))
T["news_tot"] = -((T.home_miss_off - T.home_miss_off_open) + (T.away_miss_off - T.away_miss_off_open)) + ((T.home_miss_def - T.home_miss_def_open) + (T.away_miss_def - T.away_miss_def_open))
T["form_sp"] = T.h_mg_std - T.a_mg_std; T["form10_sp"] = T.h_mg10 - T.a_mg10
T["pace_tot"] = T.h_pf_std + T.h_pa_std + T.a_pf_std + T.a_pa_std   # 2x expected total from season averages
T["rest_diff"] = T.h_rest - T.a_rest; T["ats_diff"] = T.h_ats_std - T.a_ats_std; T["ou_both"] = T.h_ou_std + T.a_ou_std
T["last_sp"] = T.h_last_mg - T.a_last_mg
# targets: move toward home (spread more negative) and move up, DK open -> Pinnacle close
T["close_sp"] = T.pin_close_spread.fillna(T.dk_close_spread); T["close_tot"] = T.pin_close_total.fillna(T.dk_close_total)
T["mv_sp"] = -(T.close_sp - T.dk_open_spread); T["mv_tot"] = T.close_tot - T.dk_open_total
# what the season numbers say vs the opener
T["form_gap_sp"] = T.form_sp + T.dk_open_spread + 0.0           # + = form says home better than the opener does (ignores home court)
T["pace_gap_tot"] = T.pace_tot / 2 - T.dk_open_total
T = T[(T.h_n >= 5) & (T.a_n >= 5)].copy()
OPEN_FEATS = {"sp": ["dk_open_spread", "form_gap_sp", "form10_sp", "inj_sp_open", "rest_diff", "L_margin", "ats_diff", "last_sp"],
              "tot": ["dk_open_total", "pace_gap_tot", "inj_tot_open", "L_total", "ou_both", "h_rest", "a_rest"]}

print("1. WHAT MOVES THE LINE (DraftKings open -> Pinnacle close), all three seasons, standardized weights (pts per 1 SD)")
for mk in ("sp", "tot"):
    feats = OPEN_FEATS[mk] + ["news_" + mk]; D = T.dropna(subset=feats + ["mv_" + mk])
    X = (D[feats] - D[feats].mean()) / D[feats].std(); y = D["mv_" + mk]
    m = RidgeCV(alphas=[0.1, 1, 10]).fit(X, y)
    r2 = m.score(X, y); r2_news = RidgeCV().fit(X[["news_" + mk]], y).score(X[["news_" + mk]], y)
    print(f"  {'spread' if mk == 'sp' else 'total'}: {len(D)} games, avg |move| {y.abs().mean():.2f}; explained {r2:.0%} (injury news after the open alone {r2_news:.0%})")
    for f, b in sorted(zip(feats, m.coef_), key=lambda z: -abs(z[1])): print(f"     {f:16s} {b:+.2f}")

print("\n2. SHARP MODEL: predict the move from what's known at DraftKings' open (train 2 seasons, test the 3rd)")
for mk in ("sp", "tot"):
    feats = OPEN_FEATS[mk]; D = T.dropna(subset=["mv_" + mk, "dk_open_spread", "dk_open_total"]).copy()
    for kind in ("ridge", "boosted"):
        D[f"pred_{kind}"] = np.nan
        for test in (2022, 2023, 2024):
            tr, te = D[D.season != test], D[D.season == test]
            if kind == "ridge":
                trc = tr.dropna(subset=feats); mu, sd = trc[feats].mean(), trc[feats].std()
                m = RidgeCV(alphas=[1, 10, 100]).fit((trc[feats] - mu) / sd, trc["mv_" + mk])
                tec = te.dropna(subset=feats); D.loc[tec.index, f"pred_{kind}"] = m.predict((tec[feats] - mu) / sd)
            else:
                m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=40).fit(tr[feats], tr["mv_" + mk])
                D.loc[te.index, f"pred_{kind}"] = m.predict(te[feats])
        for test in (2022, 2023, 2024, "all"):
            s = D if test == "all" else D[D.season == test]; s = s.dropna(subset=[f"pred_{kind}"])
            r = np.corrcoef(s[f"pred_{kind}"], s["mv_" + mk])[0, 1]
            out = [f"r={r:+.2f}"]
            for k in (0.5, 1.0, 1.5):
                b = s[s[f"pred_{kind}"].abs() >= k]
                res = (b.margin + b.dk_open_spread) * np.sign(b[f"pred_{kind}"]) if mk == "sp" else (b.pts - b.dk_open_total) * np.sign(b[f"pred_{kind}"])
                clv = b["mv_" + mk] * np.sign(b[f"pred_{kind}"])
                w, l = (res > 0).sum(), (res < 0).sum()
                out.append(f"{k}+: {w + l} bets {w / max(w + l, 1):.1%} {w * 100 / 110 - l:+.1f}u, line moved our way {(clv > 0).mean():.0%}")
            print(f"  {'spread' if mk == 'sp' else 'total'} {kind:7s} {test}: " + " | ".join(out))
    D.to_csv(os.path.join(W, "analysis", f"sharp_replicate_{mk}.csv"), index=False)
