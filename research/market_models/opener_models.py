"""Market models step 2b: opener models for NBA totals (DraftKings, Pinnacle, FanDuel).
Follows research/market_models/STEP2_OPENER_PREREG.md (written before fitting).

Walk-forward: within a scored season, models are refit every 14 days on all games dated before the block,
so team-by-season effects can learn the current season without seeing the future.
Choice: models fit through 2023-24 and walked through 2024-25 (validation); the lowest-MAE model per book is
then walked through 2025-26 (test) and scored once.
Run from repo root: python research/market_models/opener_models.py
"""
import json
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

G = pd.read_csv("research/market_models/opener_data.csv.gz", parse_dates=["tip"])
G = G.dropna(subset=["fund_total", "mkt_total"]).sort_values("tip").reset_index(drop=True)
G["d"] = pd.to_datetime(G.date)
INJ = [c for c in G.columns if c.endswith("_open") and ("miss" in c or "n_out" in c)]
BASE = ["fund_total", "mkt_total", "league_lvl", "exp_pace", "h_e_ortg", "h_e_drtg", "a_e_ortg", "a_e_drtg",
        "h_e_pace", "a_e_pace", "h_operr", "a_operr", "h_opmv", "a_opmv", "h_rest", "a_rest", "b2b_h", "b2b_a",
        "gp_min", "month"] + INJ
BOOKS = {"dk": "DraftKings", "pin": "Pinnacle", "fd": "FanDuel"}
OUT = "research/market_models/"


def feats(b):
    return BASE + [f"{b}_lead"]


for b in BOOKS:
    G[f"{b}_lead"] = np.log1p(G[f"{b}_open_lead_h"])

# ---------- models ----------
def X_of(df, cols, med):
    return df[cols].fillna(med).to_numpy(float)


def fit_predict(kind, tr, te, cols, y, lam=None):
    med = tr[cols].median()
    Xtr, Xte = X_of(tr, cols, med), X_of(te, cols, med)
    if kind == "naive":
        return te.mkt_total.to_numpy() + (tr[y] - tr.mkt_total).mean()  # recent closes, with the average offset
    if kind == "boost":
        m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.04, max_leaf_nodes=15,
                                          min_samples_leaf=40, l2_regularization=1.0, random_state=0)
        return m.fit(Xtr, tr[y]).predict(Xte)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    A = np.c_[np.ones(len(tr)), (Xtr - mu) / sd]; B = np.c_[np.ones(len(te)), (Xte - mu) / sd]
    if kind == "linear":
        beta = np.linalg.lstsq(A, tr[y].to_numpy(), rcond=None)[0]
        return B @ beta
    # mixed: + team-by-season total tendency (both teams' effects add), shrunk with ratio lam (BLUP)
    keys = sorted(set((tr.season.astype(str) + tr.home).tolist() + (tr.season.astype(str) + tr.away).tolist()))
    idx = {k: i for i, k in enumerate(keys)}
    def Z(df):
        z = np.zeros((len(df), len(keys)))
        for r, (s, h, a) in enumerate(zip(df.season.astype(str), df.home, df.away)):
            for k in (s + h, s + a):
                if k in idx: z[r, idx[k]] += 1
        return z
    Ztr, Zte = Z(tr), Z(te)
    # stacked least squares (numerically stable); tiny 1e-3 ridge on fixed slopes, none on the intercept
    M = np.c_[A, Ztr]
    pen = np.sqrt(np.array([0.0] + [1e-3] * (A.shape[1] - 1) + [lam] * Ztr.shape[1]))
    beta = np.linalg.lstsq(np.r_[M, np.diag(pen)], np.r_[tr[y].to_numpy(), np.zeros(M.shape[1])], rcond=None)[0]
    return np.c_[B, Zte] @ beta


def walk(kind, season, b, lam=None, step_days=14):
    y = f"{b}_open_point"; cols = feats(b)
    S = G[(G.season == season) & G[y].notna()]
    out = pd.Series(np.nan, index=S.index)
    start = S.d.min()
    while start <= S.d.max():
        end = start + pd.Timedelta(days=step_days)
        te = S[(S.d >= start) & (S.d < end)]
        if len(te):
            tr = G[(G.d < start) & G[y].notna()]
            out.loc[te.index] = fit_predict(kind, tr, te, cols, y, lam)
        start = end
    return out


def mae(p, b, idx):
    return float((G.loc[idx, f"{b}_open_point"] - p).abs().mean())


# ---------- 1. validation on 2024-25: pick model and shrinkage per book ----------
LAMS = [5, 20, 80]
val, choice = {}, {}
for b in BOOKS:
    val[b] = {}
    for k in ["naive", "linear", "boost"]:
        p = walk(k, 2025, b); val[b][k] = round(mae(p, b, p.index), 3)
    for lam in LAMS:
        p = walk("mixed", 2025, b, lam); val[b][f"mixed_l{lam}"] = round(mae(p, b, p.index), 3)
    best = min(val[b], key=val[b].get)
    choice[b] = best
    print(b, "validation MAE 2024-25:", val[b], "->", best)

# ---------- 2. test on 2025-26 (scored once) ----------
test, P = {}, {}
for b in BOOKS:
    test[b] = {}
    for k in ["naive", "linear", "boost", "mixed"]:
        lam = None
        if k == "mixed":
            lam = int(min((v, kk) for kk, v in val[b].items() if kk.startswith("mixed"))[1].split("_l")[1])
        p = walk(k, 2026, b, lam)
        test[b][k] = round(mae(p, b, p.index), 3)
        tag = choice[b].split("_l")[0]
        if k == tag: P[b] = p
    print(b, "test MAE 2025-26:", test[b], "| chosen:", choice[b])

# keep chosen predictions for both scored seasons (validation one is exploratory)
rows = []
for season in (2025, 2026):
    S = G[G.season == season].copy()
    for b in BOOKS:
        tag = choice[b]; lam = int(tag.split("_l")[1]) if tag.startswith("mixed") else None
        p = P[b] if season == 2026 else walk(tag.split("_l")[0], 2025, b, lam)
        S[f"{b}_pred"] = p
        S[f"{b}_resid"] = S[f"{b}_open_point"] - S[f"{b}_pred"]
    rows.append(S)
R = pd.concat(rows)
keep = ["date", "season", "home", "away", "final_total"] + [f"{b}_{c}" for b in BOOKS for c in
        ["open_point", "open_over_px", "open_under_px", "open_lead_h", "close_point", "pred", "resid"]]
R[keep].to_csv(OUT + "opener_residuals.csv", index=False)


# ---------- 3. residual tests ----------
def am_to_units(px):
    px = 110 * -1 if pd.isna(px) else px
    return px / 100 if px > 0 else 100 / -px


def bet_test(S, b, thr):
    r = S[f"{b}_resid"]; sel = S[r.abs() >= thr]
    if not len(sel): return {"n": 0}
    under = sel[f"{b}_resid"] > 0
    line = sel[f"{b}_open_point"]; close = sel[f"{b}_close_point"]
    clv = np.where(under, line - close, close - line)
    win = np.where(under, sel.final_total < line, sel.final_total > line)
    push = sel.final_total == line
    px = np.where(under, sel[f"{b}_open_under_px"], sel[f"{b}_open_over_px"])
    units = np.where(push, 0.0, np.where(win, [am_to_units(p) for p in px], -1.0))
    dec = ~push
    return {"n": int(len(sel)), "unders": int(under.sum()), "clv_pts": round(float(clv.mean()), 2),
            "clv_pos_share": round(float((clv > 0).mean()), 3), "units": round(float(units.sum()), 2),
            "roi": round(float(units.sum() / len(sel)), 3), "win_rate": round(float(win[dec].mean()), 3)}


report = {"validation_mae_2024_25": val, "chosen": choice, "test_mae_2025_26": test, "bets": {}, "corr": {}}
for season in (2025, 2026):
    S = R[R.season == season]
    for b in BOOKS:
        r = S[f"{b}_resid"]
        report["corr"][f"{season}_{b}"] = {
            "resid_vs_move(close-open)": round(float(r.corr(S[f"{b}_close_point"] - S[f"{b}_open_point"])), 3),
            "resid_vs_error(final-open)": round(float(r.corr(S.final_total - S[f"{b}_open_point"])), 3),
            "resid_sd": round(float(r.std()), 2)}
        for thr in (2.0, 3.0, 4.0):
            tag = "PREREG" if (season == 2026 and thr == 3.0 and b == "dk") else "exploratory"
            report["bets"][f"{season}_{b}_thr{thr}"] = {**bet_test(S, b, thr), "status": tag}
S = R[R.season == 2026]
report["corr"]["2026_dk_resid_vs_pin_resid"] = round(float(S.dk_resid.corr(S.pin_resid)), 3)

# what each book's opener leans on: standardized linear weights, fit on 2021-22..2024-25
lean = {}
for b in BOOKS:
    tr = G[(G.season <= 2025) & G[f"{b}_open_point"].notna()]; cols = feats(b)
    Xs = X_of(tr, cols, tr[cols].median()); Xs = (Xs - Xs.mean(0)) / (Xs.std(0) + 1e-9)
    beta = np.linalg.lstsq(np.c_[np.ones(len(tr)), Xs], tr[f"{b}_open_point"], rcond=None)[0][1:]
    lean[b] = dict(sorted({c: round(float(v), 2) for c, v in zip(cols, beta)}.items(), key=lambda kv: -abs(kv[1]))[:8])
report["linear_weights_top8"] = lean
json.dump(report, open(OUT + "opener_results.json", "w"), indent=1)
print(json.dumps({k: report[k] for k in ["bets", "corr", "linear_weights_top8"]}, indent=1))
