"""Stale-line rule v2 coefficients (Nov 5, 2026). Evidence: NCAAM repo ncaab/research/STALE_LINE_LAYERS_RESULTS_2026-11-05.md (S1).
BLEND-C v2: DK close margin ~ const + M2 + M8 + MKTL + opener + 8 lineup/travel + 4 roster feature differences (home - away; missing -> 0), OLS,
fitted like the live v1 file (all seasons <= 2025-26: SBR open/close <= 2021 with |open - close| < 6, book's own opener and close from 2024; both teams 3+ games, no OTHER).
Threshold: v2 bets the same number of games as v1's 0.5 rule did in the backtest (matched counts); the live cut-off is the mean of the per-season cut-offs
on DK 2023-24 and 2025-26 (expanding-window predictions, as graded). Also checks that the same code reproduces v1's live_blendc.json.
  python ncaab/live_blendc_v2_fit.py WORKDIR -> ncaab/data/live_blendc_v2.json (+ printed checks)"""
import os, sys, json
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
P = pd.read_csv(os.path.join(W, "ncaab", "data", "model3_preds.csv"), low_memory=False); P["date"] = pd.to_datetime(P.date)
for f in ("lineup_travel_features.csv.gz", "roster_features.csv.gz"):
    F = pd.read_csv(os.path.join(W, "derived", f)); F = F.drop(columns=[c for c in ("season", "date") if c in F.columns]); P = P.merge(F, on="espn_id", how="left")
long = pd.concat([P[["season", "date", "hk"]].rename(columns={"hk": "k"}), P[["season", "date", "ak"]].rename(columns={"ak": "k"})]).sort_values("date")
long["n"] = long.groupby(["season", "k"]).cumcount(); fg = long.groupby(["season", "k", "date"]).n.min()
P["hn"] = [fg.get((s, k, d), 0) for s, k, d in zip(P.season, P.hk, P.date)]; P["an"] = [fg.get((s, k, d), 0) for s, k, d in zip(P.season, P.ak, P.date)]
ok = ((P.hk != "OTHER") & (P.ak != "OTHER") & (np.minimum(P.hn, P.an) >= 3)).values; sbr = (P.season <= 2021).values
so, sc = -P.open_sp, -P.close_sp; sbr_ok = sbr & so.notna().values & sc.notna().values & ((so - sc).abs() < 6).values
opener = pd.Series(np.where(sbr, so, -P.book_sp), index=P.index); opener[sbr & ~sbr_ok] = np.nan
close = pd.Series(np.where(sbr | (P.season >= 2024).values, sc, np.nan), index=P.index)
LF = ["lost_min_share", "lost_pts_share", "new_starters", "travel_miles", "tz_shift", "rest_days", "back_to_back", "games_last_7"]; RF = ["R1", "R2", "R3", "R4"]
X0 = np.column_stack([np.ones(len(P)), P.M2_m, P.M8_m, P.MKTL_m, opener])
X1 = np.column_stack([X0] + [(P["h_" + f] - P["a_" + f]).fillna(0).values for f in LF + RF])
y = close.values
def fit(X, upto): tr = (P.season <= upto).values & ok & ~np.isnan(X).any(axis=1) & ~np.isnan(y); return np.linalg.lstsq(X[tr], y[tr], rcond=None)[0], int(tr.sum())
b0, n0 = fit(X0, 2026); old = json.load(open(os.path.join(W, "ncaab", "data", "live_blendc.json")))["coef"]
print("v1 refit on <= 2025-26:", np.round(b0, 4).tolist(), "| live_blendc.json:", np.round(old, 4).tolist(), "| max diff", float(np.max(np.abs(b0 - np.array(old)))))
b1, n1 = fit(X1, 2026); print("v2 coefficients (rows %d):" % n1, np.round(b1, 4).tolist())
# matched-count threshold from the graded backtest (expanding window: fit on seasons < s)
flip = (np.sign(P.book_sp) != np.sign(P.close_sp)) & (np.sign(P.book_sp) != np.sign(P.open_sp)) & (P.book_sp.abs() >= 1)
cuts = {}
for s in (2024, 2026):
    c0, _ = fit(X0, s - 1); c1, _ = fit(X1, s - 1)
    rows = (P.season == s).values & (P.book == "DraftKings").values & ok & opener.notna().values & close.notna().values & ~flip.values & ((P.book_sp - P.close_sp).abs() <= 10).values
    rows &= ~np.isnan(X1).any(axis=1) & P.home_pts.notna().values
    e0 = X0[rows] @ c0 - opener.values[rows]; e1 = X1[rows] @ c1 - opener.values[rows]; n = int((np.abs(e0) >= 0.5).sum())
    cuts[s] = float(np.sort(np.abs(e1))[::-1][n - 1]); print(f"season {s}: v1 bets {n}; v2 cut-off for the same count {cuts[s]:.4f}")
thr = round(float(np.mean(list(cuts.values()))), 3); print("live v2 threshold (mean):", thr)
json.dump(dict(coef=[float(x) for x in b1], features=["const", "M2", "M8", "MKTL", "opener"] + LF + RF, edge=thr, cuts=cuts,
               fitted_on="seasons <= 2025-26 (SBR, DK, ESPN BET), Nov 5 2026; v2 = v1 + layer features (NCAAM STALE_LINE_LAYERS_RESULTS_2026-11-05.md)"),
          open(os.path.join(W, "ncaab", "data", "live_blendc_v2.json"), "w"), indent=1)
