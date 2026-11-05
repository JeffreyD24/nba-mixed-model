"""Build the live movement model (step 3, no injury inputs) with the shared code in market_models_core.py.
1) Reproduce the leak-free pre-registered test (fit 2022-23..2024-25, test 2025-26) through the shared code: must match
   movement_results_noinj.json (593 bets, CLV +1.47, -8.0u).
2) Fit the live model on 2022-23..2025-26 and export it to data/movement_model_v1.json (numpy-only evaluation, checked
   against scikit-learn's own predictions).
Run from repo root: python research/market_models/export_movement_model.py
"""
import glob, json, sys
sys.path.insert(0, ".")
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
import market_models_core as C

# --an: Action Network-compatible variant (STEP3_MOVEMENT_PREREG.md addendum): five books both feeds have, no Pinnacle inputs
AN = "--an" in sys.argv
FEAT = C.MOVE_FEAT_AN if AN else C.MOVE_FEAT
BOOKS = C.AN_BOOKS if AN else None
OUTF = ("data/movement_model_v1an.json" if AN else "data/movement_model_v1.json")
if "--reach" in sys.argv: OUTF = OUTF.replace(".json", "_reach.json")

d = C.read_odds(sorted(glob.glob("data/odds_history/nba/*.csv.gz")))
ps = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("data/player_stats/season_*.csv.gz"))])
tr0 = pd.read_csv("data/training_games.csv")
G = C.build_games(C.first_close(d), ps, tr0[["date", "home", "away", "home_pts", "away_pts"]])
G = G[G.season.between(2022, 2026)].dropna(subset=["fund_total", "mkt_total"]).sort_values("tip").reset_index(drop=True)
G["d"] = pd.to_datetime(G.date)

# walk-forward opener predictions (14-day refits on earlier games only), seasons 2022-23..2025-26
G["dk_opred"] = np.nan
for s in (2023, 2024, 2025, 2026):
    S = G[(G.season == s) & G.dk_open_point.notna()]
    start = S.d.min()
    while start <= S.d.max():
        end = start + pd.Timedelta(days=14)
        te = S[(S.d >= start) & (S.d < end)]
        if len(te):
            m = C.fit_opener(G[(G.d < start) & G.dk_open_point.notna()])
            G.loc[te.index, "dk_opred"] = C.opener_pred(m, te)
        start = end

P = C.snapshot_panel(d, books=BOOKS, games=G[["date", "home", "away", "season", "final_total", "dk_open_point", "dk_close_point", "dk_opred"]])
P["target"] = P.dk_close_point - P.dk_now
last = P.groupby(["date", "home"]).snap.transform("max")
P = P[(P.snap < last) & (P.lead_h >= 0.5) & P.dk_opred.notna()].copy()
# REACH (Fable check, Nov 5): only snapshots the live code could price, i.e. after the morning run that follows both teams'
# previous games (the team features are keyed by date, so earlier snapshots would use a box score not played yet), and 48 h or less
REACH = "--reach" in sys.argv
if REACH:
    rt = C.ready_time(tr0)
    P = P.merge(rt, on=["date", "home", "away"], how="left")
    P = P[(P.ready_at.isna() | (P.snap >= P.ready_at)) & (P.lead_h <= 48)].copy()
P["w"] = 1 / P.groupby(["date", "home"]).snap.transform("count")
PARAMS = dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200, l2_regularization=1.0, random_state=0)


def fit(tr):
    med = tr[FEAT].median()
    return HistGradientBoostingRegressor(**PARAMS).fit(C.move_design(tr, med, FEAT), tr.target, sample_weight=tr.w), med


def am_units(p):
    p = -110 if pd.isna(p) else p
    return p / 100 if p > 0 else 100 / -p


# ---- 1) reproduce the pre-registered test
m, med = fit(P[P.season.isin([2023, 2024, 2025])])
te = P[P.season == 2026].copy()
te["pred"] = m.predict(C.move_design(te, med, FEAT))
first = te[te.pred.abs() >= 1.5].sort_values("snap").groupby(["date", "home"]).head(1)
over = first.pred > 0
clv = np.where(over, first.dk_close_point - first.dk_now, first.dk_now - first.dk_close_point)
win = np.where(over, first.final_total > first.dk_now, first.final_total < first.dk_now); push = first.final_total == first.dk_now
u = np.where(push, 0, np.where(win, [am_units(p) for p in np.where(over, first.price_o, first.price_u)], -1.0))
print(f"{'AN variant test 2025-26' if AN else 'reproduction (shared code)'}: {len(first)} bets, CLV {clv.mean():+.2f} "
      f"(se {clv.std() / np.sqrt(len(clv)):.2f}), {u.sum():+.1f}u, win {win[~push].mean():.3f}" + ("" if AN else "  (research: 593 bets, CLV +1.47, -8.0u)"))
# validation season too (exploratory), and the move-prediction error vs "no move"
mv, medv = fit(P[P.season.isin([2023, 2024])])
va = P[P.season == 2025].copy(); va["pred"] = mv.predict(C.move_design(va, medv, FEAT))
fv = va[va.pred.abs() >= 1.5].sort_values("snap").groupby(["date", "home"]).head(1); ov = fv.pred > 0
clvv = np.where(ov, fv.dk_close_point - fv.dk_now, fv.dk_now - fv.dk_close_point)
wv = np.where(ov, fv.final_total > fv.dk_now, fv.final_total < fv.dk_now); pv = fv.final_total == fv.dk_now
uv = np.where(pv, 0, np.where(wv, [am_units(p) for p in np.where(ov, fv.price_o, fv.price_u)], -1.0))
print(f"  2024-25 (exploratory): {len(fv)} bets, CLV {clvv.mean():+.2f}, {uv.sum():+.1f}u")
wm = lambda df, pr: float(np.average((df.target - pr) ** 2, weights=df.w))
print(f"  2025-26 move error: model {wm(te, te.pred):.3f} vs no move {wm(te, 0):.3f}")
first[["date", "home", "away", "snap", "lead_h", "dk_now", "dk_close_point", "final_total", "pred"]].assign(clv=clv, units=u).to_csv(
    "research/market_models/movement_bets_2025_26" + ("_an" if AN else "_noinj") + ("_reach" if "--reach" in sys.argv else "") + ".csv", index=False)

# ---- 2) live model on all four seasons
m, med = fit(P[P.season.isin([2023, 2024, 2025, 2026])])
trees = []
for it in m._predictors:
    nd = it[0].nodes
    trees.append(dict(f=nd["feature_idx"].tolist(), th=nd["num_threshold"].tolist(), l=nd["left"].tolist(), r=nd["right"].tolist(),
                      leaf=nd["is_leaf"].astype(int).tolist(), v=nd["value"].tolist(), nl=nd["missing_go_to_left"].astype(int).tolist()))
out = dict(version="movement v1-an" if AN else "movement v1", trained_on="2022-23 to 2025-26 DK totals (The Odds API snapshots), no injury inputs" + (", Action Network books only, no Pinnacle" if AN else ""),
           features=FEAT, med=[float(x) for x in med], baseline=float(np.ravel(m._baseline_prediction)[0]), trees=trees,
           bet_threshold=1.5, min_lead_h=0.5, prereg="research/market_models/STEP3_MOVEMENT_PREREG.md")
X = C.move_design(P, med, FEAT)
diff = np.abs(C.tree_predict(out, X) - m.predict(X)).max()
print("numpy vs scikit-learn max difference:", diff)
assert diff < 1e-6
json.dump(out, open(OUTF, "w"))
print("saved", OUTF, len(trees), "trees")
