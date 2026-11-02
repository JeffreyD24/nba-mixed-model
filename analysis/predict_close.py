"""
Can we predict where the NBA line will CLOSE using only what was known when it OPENED? If so, bet at the open in the
direction of the predicted move (beat the sharps to it). 2024-25 and 2025-26: train on one season, test on the other.
Inputs known at the open: Model 1's walk-forward number with the opening injury report, the opening line itself,
back-to-backs, injuries already out at the open, season-to-date shooting luck (analysis/shot_quality.py), and each
team's season-to-date results vs the closing line (what the betting public sees as hot/cold).
  python analysis/predict_close.py WORKDIR   (needs _tmp/model1_open_preds.csv from Model 1's walk-forward)
"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
P = pd.read_csv(os.path.join(W, "_tmp", "model1_open_preds.csv")); P["date"] = pd.to_datetime(P.date).dt.strftime("%Y-%m-%d")
Q = pd.read_csv(os.path.join(W, "analysis", "shot_quality_games.csv"))
Q = Q[["date", "home", "away"] + [c for c in Q if c.startswith(("h_pre_", "a_pre_")) or c in ("L_margin", "L_total")]]
G = P.merge(Q, on=["date", "home", "away"], how="left")
G["margin"] = G.home_pts - G.away_pts; G["pts_total"] = G.home_pts + G.away_pts
# season-to-date cover margin (vs the close) per team, before each game; and last 5
rows = []
for r in G.itertuples():
    cov = r.margin + r.spread
    rows += [dict(i=r.Index, season=r.season, date=r.date, team=r.home, cov=cov, ov=r.pts_total - r.total),
             dict(i=r.Index, season=r.season, date=r.date, team=r.away, cov=-cov, ov=r.pts_total - r.total)]
TT = pd.DataFrame(rows).sort_values(["season", "team", "date"])
g = TT.groupby(["season", "team"])
TT["ats_pre"] = g["cov"].transform(lambda v: v.shift().expanding().mean()); TT["ats5"] = g["cov"].transform(lambda v: v.shift().rolling(5, min_periods=3).mean())
TT["ov_pre"] = g["ov"].transform(lambda v: v.shift().expanding().mean())
for col in ("ats_pre", "ats5", "ov_pre"):
    m = TT.set_index(["i", "team"])[col]
    G[f"h_{col}"] = [m.get((i, t), np.nan) for i, t in zip(G.index, G.home)]
    G[f"a_{col}"] = [m.get((i, t), np.nan) for i, t in zip(G.index, G.away)]
# targets: market move toward HOME (spread got more negative) and total move up
G["mv_sp"] = -(G.spread - G.open_spread); G["mv_tot"] = G.total - G.open_total
G["e_sp"] = G.pred_margin + G.open_spread          # model likes home by this much vs the opener
G["e_tot"] = G.pred_total - G.open_total
G["inj_sp"] = (G.away_miss_off_open + G.home_miss_def_open) - (G.home_miss_off_open + G.away_miss_def_open)
G["b2b_diff"] = G.b2b_away.astype(float) - G.b2b_home.astype(float)
G["ats_diff"] = G.h_ats_pre - G.a_ats_pre; G["ats5_diff"] = G.h_ats5 - G.a_ats5
G["ov_both"] = G.h_ov_pre + G.a_ov_pre
FS = {"spread": ["e_sp", "open_spread", "inj_sp", "b2b_diff", "L_margin", "ats_diff", "ats5_diff"],
      "total": ["e_tot", "open_total", "L_total", "ov_both", "b2b_diff"]}


def ridge(X, y, lam=1.0):
    mu, sd = X.mean(0), X.std(0) + 1e-9; Z = (X - mu) / sd
    b = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return lambda X2: ((X2 - mu) / sd) @ b + y.mean(), dict(zip(range(len(b)), b))


for mk, feats in FS.items():
    tgt = "mv_sp" if mk == "spread" else "mv_tot"
    D = G.dropna(subset=feats + [tgt]).copy()
    print(f"\n=== {mk.upper()}: {len(D)} games with every input. Average |move| open->close: {D[tgt].abs().mean():.2f} pts; "
          f"moved at all: {(D[tgt] != 0).mean():.0%}")
    D["pred"] = np.nan; D["pred_base"] = np.nan
    for test in (2025, 2026):
        tr, te = D[D.season != test], D[D.season == test]
        f, b = ridge(tr[feats].values, tr[tgt].values); D.loc[te.index, "pred"] = f(te[feats].values)
        f0, _ = ridge(tr[[feats[0]]].values, tr[tgt].values); D.loc[te.index, "pred_base"] = f0(te[[feats[0]]].values)
        print(f"  trained on {[s for s in (2025, 2026) if s != test][0]}: weights " +
              ", ".join(f"{n} {v:+.2f}" for n, v in zip(feats, b.values())))
    for col, lab in (("pred_base", "model edge only"), ("pred", "all inputs")):
        r = np.corrcoef(D[col], D[tgt])[0, 1]
        print(f"  {lab:16s}: correlation with the actual move {r:+.3f} (out of season)")
    # bet at the open in the direction of the predicted move; result vs the open, plus closing line value
    for col, lab in (("pred_base", "model edge only"), ("pred", "all inputs")):
        for k in (0.5, 1.0, 1.5):
            s = D[D[col].abs() >= k]
            if mk == "spread":
                res = (s.margin + s.open_spread) * np.sign(s[col]); clv = s[tgt] * np.sign(s[col])
            else:
                res = (s.pts_total - s.open_total) * np.sign(s[col]); clv = s[tgt] * np.sign(s[col])
            w, l = int((res > 0).sum()), int((res < 0).sum())
            print(f"    {lab:16s} predicted move {k}+: {w + l:4d} bets at the open, won {w / max(w + l, 1):.1%}, "
                  f"line moved our way {(clv > 0).mean():.0%} / against {(clv < 0).mean():.0%}, avg CLV {clv.mean():+.2f} pts")
G.to_csv(os.path.join(W, "analysis", "predict_close_games.csv"), index=False)
