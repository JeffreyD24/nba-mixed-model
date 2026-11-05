"""
NCAAM Model 1 (Nov 5, 2026): ridge mixed model of team points, refit every game day, walk-forward (pre-registration:
ncaab/research/NCAAM_PREREG_2026-11-05.md). Two rows per game:
  points(team) = mu + offense(team) + defense(opponent) + hca x h + e,   h = +0.5 home, -0.5 away, 0 neutral
Offense / defense are shrunk (ridge) toward last season's final rating x carryover; games weighted by recency.
Non-D1 teams share one effect ("NOND1").
  python ncaab/model.py WORKDIR --tune            (grid on 2022-23 results only, 2021-22 warm-up; no lines used)
  python ncaab/model.py WORKDIR --predict R C H    (walk-forward predictions every season -> ncaab/data/preds.csv)
"""
import os, sys, itertools, json
import numpy as np, pandas as pd
import scipy.sparse as sp

W = os.path.abspath(sys.argv[1]); D = os.path.join(W, "ncaab", "data")


def load():
    G = pd.read_csv(os.path.join(D, "games.csv"))
    G = G[G.home_pts.notna() & (G.home_pts + G.away_pts > 60)].copy()
    G["date"] = pd.to_datetime(G.date)
    G["hk"] = np.where(G.home_d1, G.home_id.astype(str), "NOND1"); G["ak"] = np.where(G.away_d1, G.away_id.astype(str), "NOND1")
    amb = G.duplicated(["date", "home_pts", "away_pts"], keep=False) | ~G.espn_match.astype(bool)
    G["neutral_ok"] = ~amb
    G["h"] = np.where(amb, 0.25, np.where(G.neutral.fillna(False).astype(bool), 0.0, 0.5))   # ambiguous: half home (ratings only)
    # regulation-only points would be better for totals; OT games are kept as played (periods > 2 flagged)
    return G.sort_values(["date", "start"]).reset_index(drop=True)


def run_season(S, teams, prior, ridge, half, keep_days=None):
    """walk-forward over one season's game days -> predictions per game, and final ratings"""
    ix = {t: i for i, t in enumerate(teams)}; n = len(teams); p = 2 + 2 * n        # mu, hca, off[n], def[n]
    hi, ai = S.hk.map(ix).values, S.ak.map(ix).values
    # rows: home scoring (off home, def away, +h) and away scoring (off away, def home, -h)
    rows = np.r_[np.arange(len(S)), np.arange(len(S))]
    def design(idx):
        m = len(idx); r = np.arange(2 * m)
        cols = [np.zeros(2 * m, int), np.ones(2 * m, int), 2 + np.r_[hi[idx], ai[idx]], 2 + n + np.r_[ai[idx], hi[idx]]]
        vals = [np.ones(2 * m), np.r_[S.h.values[idx], -S.h.values[idx]], np.ones(2 * m), np.ones(2 * m)]
        return sp.csr_matrix((np.concatenate(vals), (np.tile(r, 4), np.concatenate(cols))), shape=(2 * m, p))
    y_all = np.r_[S.home_pts.values, S.away_pts.values]
    pr = np.zeros(p); pr[2:2 + n] = [prior.get(("o", t), 0.0) for t in teams]; pr[2 + n:] = [prior.get(("d", t), 0.0) for t in teams]
    pen = np.full(p, ridge); pen[:2] = 1e-6
    out_m, out_t = np.full(len(S), np.nan), np.full(len(S), np.nan)
    days = np.sort(S.date.unique()); b = pr.copy(); b[0] = prior.get("mu", 70.0); b[1] = prior.get("hca", 3.0)
    dates = S.date.values
    for d in days:
        today = np.where(dates == d)[0]
        past = np.where(dates < d)[0]
        if len(past) >= 50:
            age = (d - dates[past]).astype("timedelta64[D]").astype(float)
            w = 0.5 ** (age / half) if half else np.ones(len(past))
            X = design(past); ww = np.r_[w, w]; y = np.r_[S.home_pts.values[past], S.away_pts.values[past]]
            A = (X.T.multiply(ww)) @ X; A = A.toarray() + np.diag(pen)
            rhs = X.T @ (ww * y) + pen * np.r_[0, 0, pr[2:]]
            b = np.linalg.solve(A, rhs)
        X = design(today); f = X @ b; m = len(today)
        out_m[today] = f[:m] - f[m:]; out_t[today] = f[:m] + f[m:]
    rat = {("o", t): b[2 + i] for i, t in enumerate(teams)}; rat.update({("d", t): b[2 + n + i] for i, t in enumerate(teams)})
    rat["mu"], rat["hca"] = b[0], b[1]
    return out_m, out_t, rat


def walk(G, ridge, carry, half, seasons):
    teams = sorted(set(G.hk) | set(G.ak)); prior = {}; res = []
    for s in seasons:
        S = G[G.season == s].reset_index(drop=True)
        pc = {k: (v * carry if isinstance(k, tuple) and k[1] != "NOND1" else v) for k, v in prior.items()}
        m, t, rat = run_season(S, teams, pc, ridge, half)
        res.append(S.assign(pred_margin=m, pred_total=t)); prior = rat
    return pd.concat(res, ignore_index=True)


if __name__ == "__main__":
    G = load()
    if "--tune" in sys.argv:
        rows = []
        for r, c, h in itertools.product((2, 5, 10, 20), (0.4, 0.6, 0.8), (30, 60, 120, 0)):
            P = walk(G, r, c, h, [2022, 2023]); T = P[(P.season == 2023) & P.pred_margin.notna()]
            mm = np.mean((T.home_pts - T.away_pts - T.pred_margin) ** 2); mt = np.mean((T.home_pts + T.away_pts - T.pred_total) ** 2)
            rows.append(dict(ridge=r, carry=c, half=h, mse_margin=mm, mse_total=mt)); print(rows[-1], flush=True)
        R = pd.DataFrame(rows); R["score"] = R.mse_margin / R.mse_margin.min() + R.mse_total / R.mse_total.min()
        R.sort_values("score").to_csv(os.path.join(W, "ncaab", "research", "tune_2022_23.csv"), index=False)
        print(R.sort_values("score").head(5).to_string())
    if "--predict" in sys.argv:
        i = sys.argv.index("--predict"); r, c, h = float(sys.argv[i + 1]), float(sys.argv[i + 2]), float(sys.argv[i + 3])
        P = walk(G, r, c, h, sorted(G.season.unique()))
        P.to_csv(os.path.join(D, "preds.csv"), index=False); print("saved", len(P))
