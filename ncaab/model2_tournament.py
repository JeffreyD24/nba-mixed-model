"""NCAAM Model 2 tournament: predictions (ncaab/research/MODEL2_PREREG_2026-11-05.md).
  python ncaab/model2_tournament.py WORKDIR -> ncaab/data/model2_preds.csv, ncaab/research/model2_tuning.txt"""
import os, sys, itertools
import numpy as np, pandas as pd, scipy.sparse as sp
W = os.path.abspath(sys.argv[1]); D = os.path.join(W, "ncaab", "data")
G = pd.read_csv(os.path.join(D, "all_games.csv"), low_memory=False); G["date"] = pd.to_datetime(G.date)
G = G.sort_values(["date", "espn_id"]).reset_index(drop=True)
G["hc"] = G.season.astype(str) + "_" + G.home_conf_id.fillna(-1).astype(int).astype(str)
G["ac"] = G.season.astype(str) + "_" + G.away_conf_id.fillna(-1).astype(int).astype(str)
# teams with fewer than 8 games in a season (mostly non-D-I opponents) share one effect "OTHER" for that season
G["hk"], G["ak"] = G.hk.astype(str), G.ak.astype(str)
cnt = pd.concat([G[["season", "hk"]].rename(columns={"hk": "t"}), G[["season", "ak"]].rename(columns={"ak": "t"})]).value_counts()
if "--live-rule" in sys.argv:   # Nov 5 (Fable review): pre-game-known rule -- a team with no conference id is "OTHER"
    for s_, c_ in (("hk", "home_conf_id"), ("ak", "away_conf_id")): G[s_] = np.where(G[c_].notna(), G[s_], "OTHER")
else:
    for s_ in ("hk", "ak"): G[s_] = [t if cnt.get((se, t), 0) >= 8 else "OTHER" for se, t in zip(G.season, G[s_])]
log_lines = []

def run_season(S, prior, ridge=5.0, cridge=None, level_half=None, log=False):
    TEAMS = sorted(set(S.hk) | set(S.ak)); TI = {t: i for i, t in enumerate(TEAMS)}
    n = len(TEAMS); confs = sorted(set(S.hc) | set(S.ac)) if cridge else []; nc = len(confs); CI = {c: i for i, c in enumerate(confs)}
    p = 2 + 2 * n + 2 * nc
    hi, ai = S.hk.map(TI).values, S.ak.map(TI).values; dates = S.date.values
    hp, ap = S.home_pts.values.astype(float), S.away_pts.values.astype(float)
    yh, ya = (np.log(hp), np.log(ap)) if log else (hp, ap)
    hci, aci = (S.hc.map(CI).values, S.ac.map(CI).values) if cridge else (None, None)
    def design(idx):
        m = len(idx); r = np.arange(2 * m)
        cols = [np.zeros(2 * m, int), np.ones(2 * m, int), 2 + np.r_[hi[idx], ai[idx]], 2 + n + np.r_[ai[idx], hi[idx]]]
        vals = [np.ones(2 * m), np.r_[S.h.values[idx], -S.h.values[idx]], np.ones(2 * m), np.ones(2 * m)]
        if cridge:
            cols += [2 + 2 * n + np.r_[hci[idx], aci[idx]], 2 + 2 * n + nc + np.r_[aci[idx], hci[idx]]]; vals += [np.ones(2 * m), np.ones(2 * m)]
        k = len(cols); return sp.csr_matrix((np.concatenate(vals), (np.tile(r, k), np.concatenate(cols))), shape=(2 * m, p))
    pr = np.zeros(p); pr[2:2 + n] = [prior.get(("o", t), 0.0) for t in TEAMS]; pr[2 + n:2 + 2 * n] = [prior.get(("d", t), 0.0) for t in TEAMS]
    if cridge:   # conference prior: last season's same conference id, carried
        pr[2 + 2 * n:2 + 2 * n + nc] = [prior.get(("co", c.split("_")[1]), 0.0) for c in confs]; pr[2 + 2 * n + nc:] = [prior.get(("cd", c.split("_")[1]), 0.0) for c in confs]
    pen = np.full(p, ridge); pen[:2] = 1e-6
    if cridge: pen[2 + 2 * n:] = cridge
    days = np.sort(S.date.unique()); b = pr.copy(); b[0] = prior.get("mu", np.mean(yh[:100])); b[1] = prior.get("hca", 0.0)
    level = {}
    if level_half:
        both = (yh + ya) / 2
        for d in days:
            past = dates < d
            if past.sum() >= 100:
                age = (d - dates[past]).astype("timedelta64[D]").astype(float); w = 0.5 ** (age / level_half); level[d] = float((w * both[past]).sum() / w.sum())
        lv = pd.Series(level).reindex(days); lv = lv.bfill().ffill().fillna(0.0); level = lv.to_dict()
    lev = np.array([level.get(d, 0.0) for d in dates]) if level_half else np.zeros(len(S))
    om, ot = np.full(len(S), np.nan), np.full(len(S), np.nan)
    for d in days:
        today = np.where(dates == d)[0]; past = np.where(dates < d)[0]
        if len(past) >= 100:
            X = design(past); y = np.r_[yh[past] - lev[past], ya[past] - lev[past]]
            A = (X.T @ X).toarray() + np.diag(pen); rhs = X.T @ y + pen * np.r_[0, 0, pr[2:]]
            b = np.linalg.solve(A, rhs)
        f = design(today) @ b; m = len(today); L = level.get(d, 0.0) if level_half else 0.0
        fh, fa = f[:m] + L, f[m:] + L
        if log: fh, fa = np.exp(fh), np.exp(fa)
        om[today] = fh - fa; ot[today] = fh + fa
    rat = {("o", t): b[2 + i] for i, t in enumerate(TEAMS)}; rat.update({("d", t): b[2 + n + i] for i, t in enumerate(TEAMS)})
    if cridge:
        rat.update({("co", c.split("_")[1]): b[2 + 2 * n + i] for i, c in enumerate(confs)}); rat.update({("cd", c.split("_")[1]): b[2 + 2 * n + nc + i] for i, c in enumerate(confs)})
    rat["mu"], rat["hca"] = b[0], b[1]
    return om, ot, rat

def walk(seasons, carry=0.8, **kw):
    prior = {}; M, T = [], []
    for s in seasons:
        S = G[G.season == s].reset_index(drop=True)
        pc = {k: (v * carry if isinstance(k, tuple) else v) for k, v in prior.items()}
        m, t, prior = run_season(S, pc, **kw); M.append(m); T.append(t)
    return np.concatenate(M), np.concatenate(T)

SEAS = sorted(G.season.unique()); TUNE = [2009, 2010, 2011]
tune_idx = G.season.isin(range(2008, 2012)).values
def tune_score(kw):
    m, t = walk(range(2008, 2012), **kw); g = G[tune_idx].reset_index(drop=True); k = g.season.isin(TUNE).values & ~np.isnan(m)
    return np.mean(((g.home_pts - g.away_pts).values[k] - m[k]) ** 2), np.mean(((g.home_pts + g.away_pts).values[k] - t[k]) ** 2)
res = []
for r, c in itertools.product((5, 10, 20), (1, 3, 10)):
    mm, mt = tune_score(dict(ridge=r, cridge=c)); res.append((r, c, mm, mt)); print("M8 knob", r, c, round(mm, 2), round(mt, 2), flush=True)
mm1, mt1 = tune_score({}); res.append(("M1", "-", mm1, mt1))
R = pd.DataFrame(res, columns=["ridge", "cridge", "mse_m", "mse_t"]); R8 = R[R.cridge != "-"].copy()
R8["score"] = R8.mse_m / R8.mse_m.min() + R8.mse_t / R8.mse_t.min(); best = R8.sort_values("score").iloc[0]
log_lines.append(R.round(2).to_string()); log_lines.append(f"M8 chosen: team ridge {best.ridge}, conference ridge {best.cridge}")
cfg = {"M1": {}, "M2": dict(level_half=14), "M4": dict(log=True), "M8": dict(ridge=float(best.ridge), cridge=float(best.cridge)),
       "M10": dict(ridge=float(best.ridge), cridge=float(best.cridge), level_half=14, log=True)}
P = G.copy()
for k, c in cfg.items():
    P[f"{k}_m"], P[f"{k}_t"] = walk(SEAS, **c); print("ran", k, flush=True)
    kk = P.season.isin(TUNE)
    log_lines.append(f"{k} tuning-season MSE margin {np.mean((P.home_pts - P.away_pts - P[f'{k}_m'])[kk] ** 2):.2f} total {np.mean((P.home_pts + P.away_pts - P[f'{k}_t'])[kk] ** 2):.2f}")
P.to_csv(os.path.join(D, "model2_preds.csv"), index=False)
open(os.path.join(W, "ncaab", "research", "model2_tuning.txt"), "w").write("\n".join(log_lines) + "\n"); print("\n".join(log_lines))
