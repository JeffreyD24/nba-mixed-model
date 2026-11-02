"""Does a team's last 10 games add anything our model and the line don't already have? Sharps move lines toward recent form
(sharp_replicate.py); if recent form also predicts RESULTS against the line, the model should use it.
NBA: 2023-24 (DraftKings openers), 2024-25 and 2025-26 (training openers), Model 1 walk-forward predictions.
  python analysis/form10_test.py WORKDIR"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
T = pd.read_csv(os.path.join(W, "data", "training_games.csv")).sort_values("date").reset_index(drop=True)
T["margin"] = T.home_pts - T.away_pts; T["pts"] = T.home_pts + T.away_pts
rows = []
for r in T.itertuples():
    rows += [dict(i=r.Index, side="h", season=r.season, team=r.home, date=r.date, mg=r.margin, tp=r.pts),
             dict(i=r.Index, side="a", season=r.season, team=r.away, date=r.date, mg=-r.margin, tp=r.pts)]
L = pd.DataFrame(rows).sort_values(["season", "team", "date"]); g = L.groupby(["season", "team"])
L["mg10"] = g.mg.transform(lambda v: v.shift().rolling(10, min_periods=5).mean()); L["mgS"] = g.mg.transform(lambda v: v.shift().expanding().mean())
L["tp10"] = g.tp.transform(lambda v: v.shift().rolling(10, min_periods=5).mean()); L["tpS"] = g.tp.transform(lambda v: v.shift().expanding().mean())
L["n"] = g.cumcount()
for c in ("mg10", "mgS", "tp10", "tpS", "n"):
    pv = L.pivot_table(index="i", columns="side", values=c); T[f"h_{c}"] = pv["h"]; T[f"a_{c}"] = pv["a"]
T["hot_sp"] = (T.h_mg10 - T.h_mgS) - (T.a_mg10 - T.a_mgS)       # home's recent form above its season level, minus the away team's
T["hot_tot"] = (T.h_tp10 - T.h_tpS) + (T.a_tp10 - T.a_tpS)
P1 = pd.read_csv(os.path.join(W, "_tmp", "model1_open_preds.csv")); P2 = pd.read_csv(os.path.join(W, "_tmp", "test_2024_games.csv"))
P2 = P2.assign(open_spread=P2.sp_open, open_total=P2.ov_open, total=P2.ov_close, spread=P2.sp_close)
P = pd.concat([P1[["date", "home", "away", "season", "pred_margin", "pred_total", "open_spread", "open_total", "spread", "total"]],
               P2[["date", "home", "away", "season", "pred_margin", "pred_total", "open_spread", "open_total", "spread", "total"]]])
P["date"] = pd.to_datetime(P.date).dt.strftime("%Y-%m-%d")
D = P.merge(T[["date", "home", "away", "margin", "pts", "hot_sp", "hot_tot", "h_n", "a_n"]], on=["date", "home", "away"])
D = D[(D.h_n >= 10) & (D.a_n >= 10)].dropna(subset=["open_spread", "open_total", "hot_sp"])
print(f"{len(D)} games (both teams 10+ games in)\n")
for mk in ("spread", "total"):
    if mk == "spread":
        cov_o = D.margin + D.open_spread; cov_c = D.margin + D.spread; edge = D.pred_margin + D.open_spread; hot = D.hot_sp
        mv = -(D.spread - D.open_spread)
    else:
        cov_o = D.pts - D.open_total; cov_c = D.pts - D.total; edge = D.pred_total - D.open_total; hot = D.hot_tot
        mv = D.total - D.open_total
    print(f"{mk.upper()}: recent form (last 10 vs season)")
    for s in sorted(D.season.unique()):
        k = D.season == s
        X = np.column_stack([edge[k], hot[k], np.ones(k.sum())])
        b = np.linalg.lstsq(X, cov_o[k], rcond=None)[0]
        print(f"  {s}: corr with line move {np.corrcoef(hot[k], mv[k])[0, 1]:+.3f} | with result vs open {np.corrcoef(hot[k], cov_o[k])[0, 1]:+.3f} "
              f"| vs close {np.corrcoef(hot[k], cov_c[k].fillna(0))[0, 1]:+.3f} | extra pts per pt of form, beyond our model: {b[1]:+.3f}")
    for lab, kk in (("form agrees with our bet", np.sign(hot) == np.sign(edge)), ("form against our bet", np.sign(hot) != np.sign(edge))):
        m = (edge.abs() >= 3) & kk; r = np.sign(edge[m]) * cov_o[m]; w, l = (r > 0).sum(), (r < 0).sum()
        print(f"  our edge 3+ bets, {lab}: {w + l} bets, {w / max(w + l, 1):.1%}")
print("\nAdding recent form to the model: units at the opener, edge 3+, by weight (pts added per pt of recent form)")
for mk in ("spread", "total"):
    for c in (0, 0.05, 0.1, 0.15, 0.2):
        out = []
        for s in sorted(D.season.unique()):
            k = D.season == s; d = D[k]
            if mk == "spread":
                e = d.pred_margin + c * d.hot_sp + d.open_spread; r = np.sign(e) * (d.margin + d.open_spread)
            else:
                e = d.pred_total + c * d.hot_tot - d.open_total; r = np.sign(e) * (d.pts - d.open_total)
            m = e.abs() >= 3; w, l = (r[m] > 0).sum(), (r[m] < 0).sum()
            out.append(f"{s}: {w + l} bets {w / max(w + l, 1):.1%} {w * 100 / 110 - l:+.1f}u")
        print(f"  {mk} weight {c:.2f}: " + " | ".join(out))
