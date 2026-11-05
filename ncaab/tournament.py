"""College model tournament (pre-registration: ncaab/research/TOURNAMENT_PREREG_2026-11-05.md). Both sports, one script.
  python ncaab/tournament.py NBA_REPO NFL_REPO --sport ncaam|ncaaf  -> {sport}/research/tournament_output.txt, {sport}/data/tourn_preds.csv"""
import os, sys, itertools
import numpy as np, pandas as pd, scipy.sparse as sp
NBA, NFL = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]); SPORT = sys.argv[sys.argv.index("--sport") + 1]
ROOT, SUB = (NBA, "ncaab") if SPORT == "ncaam" else (NFL, "ncaaf")
src = open(os.path.join(ROOT, SUB, "model.py")).read().split('if __name__')[0]
ns = {"__name__": "m", "sys": sys}; sys.argv = ["x", ROOT]; exec(src, ns); G = ns["load"]()
TUNE, SEASONS = (2023, [2022, 2023, 2024, 2025, 2026, 2027]) if SPORT == "ncaam" else (2022, [2021, 2022, 2023, 2024, 2025, 2026])
SEASONS = [s for s in SEASONS if s in set(G.season)]
FBASE = 2 if SPORT == "ncaam" else None
if SPORT == "ncaam":
    ot = (G.periods.fillna(2) - 2).clip(lower=0); G["reg_f"] = 40 / (40 + 5 * ot)
else:
    G["reg_f"] = 1.0
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)


def run_season(S, teams, prior, ridge, level_half=None, log=False, reg=False):
    ix = {t: i for i, t in enumerate(teams)}; n = len(teams); p = 2 + 2 * n
    hi, ai = S.hk.map(ix).values, S.ak.map(ix).values; dates = S.date.values
    hp, ap = S.home_pts.values.astype(float), S.away_pts.values.astype(float)
    if reg: hp, ap = hp * S.reg_f.values, ap * S.reg_f.values
    yh, ya = (np.log(np.maximum(hp, 1)), np.log(np.maximum(ap, 1))) if log else (hp, ap)
    def design(idx):
        m = len(idx); r = np.arange(2 * m)
        cols = [np.zeros(2 * m, int), np.ones(2 * m, int), 2 + np.r_[hi[idx], ai[idx]], 2 + n + np.r_[ai[idx], hi[idx]]]
        vals = [np.ones(2 * m), np.r_[S.h.values[idx], -S.h.values[idx]], np.ones(2 * m), np.ones(2 * m)]
        return sp.csr_matrix((np.concatenate(vals), (np.tile(r, 4), np.concatenate(cols))), shape=(2 * m, p))
    pr = np.zeros(p); pr[2:2 + n] = [prior.get(("o", t), 0.0) for t in teams]; pr[2 + n:] = [prior.get(("d", t), 0.0) for t in teams]
    pen = np.full(p, ridge); pen[:2] = 1e-6
    days = np.sort(S.date.unique()); b = pr.copy(); b[0] = prior.get("mu", np.mean(yh[:50]) if len(yh) else 0); b[1] = prior.get("hca", 0.0)
    lev = np.zeros(len(S)); level_now = {}
    if level_half:     # league level for each date from earlier games only (mean of both teams' points)
        both = (yh + ya) / 2
        for d in days:
            past = dates < d
            if past.sum() >= 50:
                age = (d - dates[past]).astype("timedelta64[D]").astype(float); w = 0.5 ** (age / level_half)
                level_now[d] = float((w * both[past]).sum() / w.sum())
            else: level_now[d] = np.nan
        lv = pd.Series(level_now); first = lv.dropna().iloc[0] if lv.notna().any() else 0.0
        lv = lv.fillna(first); lev = lv.reindex(dates).values; level_now = lv.to_dict()
    om, ot_ = np.full(len(S), np.nan), np.full(len(S), np.nan); ratio = 1.0
    for d in days:
        today = np.where(dates == d)[0]; past = np.where(dates < d)[0]
        if len(past) >= 40:
            X = design(past); y = np.r_[yh[past] - lev[past], ya[past] - lev[past]]
            A = (X.T @ X).toarray() + np.diag(pen); rhs = X.T @ y + pen * np.r_[0, 0, pr[2:]]
            b = np.linalg.solve(A, rhs)
            if reg: ratio = float((S.home_pts.values[past] + S.away_pts.values[past]).sum() / (hp[past] + ap[past]).sum())
        f = design(today) @ b; m = len(today); L = level_now.get(d, 0.0) if level_half else 0.0
        fh, fa = f[:m] + L, f[m:] + L
        if log: fh, fa = np.exp(fh), np.exp(fa)
        om[today] = fh - fa; ot_[today] = (fh + fa) * (ratio if reg else 1.0)
    rat = {("o", t): b[2 + i] for i, t in enumerate(teams)}; rat.update({("d", t): b[2 + n + i] for i, t in enumerate(teams)})
    rat["mu"], rat["hca"] = b[0], b[1]
    return om, ot_, rat


def walk(seasons, ridge=5.0, carry=0.8, **kw):
    teams = sorted(set(G.hk) | set(G.ak)); prior = {}; M, T = [], []
    nd = "NOND1" if SPORT == "ncaam" else "FCS"
    for s in seasons:
        S = G[G.season == s].reset_index(drop=True)
        pc = {k: (v * carry if isinstance(k, tuple) and k[1] != nd else v) for k, v in prior.items()}
        m, t, prior = run_season(S, teams, pc, ridge, **kw); M.append(m); T.append(t)
    return np.concatenate(M), np.concatenate(T)


idx_t = np.concatenate([np.where(G.season == s)[0] for s in SEASONS])   # row order produced by walk()
GG = G.iloc[idx_t].reset_index(drop=True)
def tune_score(m, t):
    k = (GG.season == TUNE).values & ~np.isnan(m)
    return np.mean((GG.home_pts - GG.away_pts).values[k] - m[k]) ** 0 * np.mean(((GG.home_pts - GG.away_pts).values[k] - m[k]) ** 2), \
           np.mean(((GG.home_pts + GG.away_pts).values[k] - t[k]) ** 2)
tseasons = [s for s in SEASONS if s <= TUNE]
def pick(lab, grid, make):
    res = []
    for g in grid:
        m, t = walk(tseasons, **make(g)); res.append((g, *tune_score(np.r_[m, np.full(len(GG) - len(m), np.nan)], np.r_[t, np.full(len(GG) - len(t), np.nan)])))
    R = pd.DataFrame(res, columns=["knob", "mse_m", "mse_t"]); R["score"] = R.mse_m / R.mse_m.min() + R.mse_t / R.mse_t.min()
    best = R.sort_values("score").iloc[0].knob; say(f"  {lab}: knob grid {R.round(2).values.tolist()} -> chosen {best}"); return best

say(f"TOURNAMENT {SPORT.upper()} - knobs chosen on {TUNE} results only")
H = pick("M2 level half-life", [14, 30, 60], lambda g: dict(level_half=g))
RL = pick("M4 log ridge", [2, 5, 10, 20], lambda g: dict(log=True, ridge=g))
cfg = {"M1": {}, "M2": dict(level_half=H), "M4": dict(log=True, ridge=RL)}
if SPORT == "ncaam": cfg["M3"] = dict(reg=True)
cfg["M5"] = dict(level_half=H, log=True, ridge=RL, **(dict(reg=True) if SPORT == "ncaam" else {}))
P = GG.copy()
for k, c in cfg.items():
    P[f"{k}_m"], P[f"{k}_t"] = walk(SEASONS, **c); print("ran", k, flush=True)
base = [k for k in ("M1", "M2", "M3", "M4") if k in cfg]
P["M6_m"] = P[[f"{k}_m" for k in base]].mean(axis=1); P["M6_t"] = P[[f"{k}_t" for k in base]].mean(axis=1)
P.to_csv(os.path.join(ROOT, SUB, "data", "tourn_preds.csv"), index=False)

# ---- grading (same filters as Model 1)
long = pd.concat([P[["season", "date", "hk"]].rename(columns={"hk": "t"}), P[["season", "date", "ak"]].rename(columns={"ak": "t"})]).sort_values("date")
long["n"] = long.groupby(["season", "t"]).cumcount(); fg = long.groupby(["season", "t", "date"]).n.min()
P["hn"] = [fg.get((s, t, d), 0) for s, t, d in zip(P.season, P.hk, P.date)]; P["an"] = [fg.get((s, t, d), 0) for s, t, d in zip(P.season, P.ak, P.date)]
if SPORT == "ncaam":
    ok = P.home_d1 & P.away_d1 & P.neutral_ok & (np.minimum(P.hn, P.an) >= 3); TH = {"spread": 5, "total": 6}; CS = [2024, 2025, 2026]; BE = {"spread": 0.67, "total": 0.99}
else:
    ok = P.home_fbs & P.away_fbs & (P.type != "post") & P.neutral_ok & (np.minimum(P.hn, P.an) >= 3); TH = {"spread": 2, "total": 2}; CS = [2023, 2024, 2025]; BE = {"spread": 0.92, "total": 0.94}
def pay(px): px = np.where(pd.isna(px), -110, px); return np.where(px > 0, px / 100, 100 / np.abs(px))
rng = np.random.default_rng(5)
rows = []
for mk in ("spread", "total"):
    line = -P.open_spread if mk == "spread" else P.open_total; close = -P.dk_spread if mk == "spread" else P.dk_total
    res = (P.home_pts - P.away_pts) if mk == "spread" else (P.home_pts + P.away_pts)
    cpos, cneg = (P.dk_spread_px, P.dk_spread_away_px) if mk == "spread" else (P.dk_over_px, P.dk_under_px)
    say(f"\n{mk.upper()} (threshold {TH[mk]}+, break-even CLV {BE[mk]}); seasons {CS}")
    for k in list(cfg) + ["M6"]:
        mod = P[f"{k}_{'m' if mk == 'spread' else 't'}"]; e = mod - line
        sel = ok & P.season.isin(CS) & line.notna() & close.notna() & (e.abs() >= TH[mk]) & mod.notna()
        sg = np.sign(e[sel]); clv = sg * (close[sel] - line[sel]); ro = sg * (res[sel] - line[sel]); rc = sg * (res[sel] - close[sel])
        uo = np.where(ro > 0, 100 / 110, np.where(ro < 0, -1.0, 0.0)); px = np.where(sg > 0, cpos[sel], cneg[sel])
        uc = np.where(rc > 0, pay(px), np.where(rc < 0, -1.0, 0.0))
        d = P.date[sel].values; g = pd.DataFrame(dict(d=d, c=clv.values)).groupby("d").c.agg(["sum", "count"]).values
        bs = [g[i, 0].sum() / g[i, 1].sum() for i in (rng.integers(0, len(g), len(g)) for _ in range(2000))]
        acc_k = ok & P.season.isin(CS) & mod.notna(); rmse = np.sqrt(np.mean((res[acc_k] - mod[acc_k]) ** 2))
        bys = {s: float(uo[(P.season[sel] == s).values].sum()) for s in CS}
        rows.append(dict(market=mk, model=k, bets=int(sel.sum()), clv=clv.mean(), clv_lo=np.percentile(bs, 5), u_open=uo.sum(), u_close=uc.sum(),
                         roi_close=uc.mean(), win=np.mean(ro[ro != 0] > 0), rmse=rmse, **{f"u_{s}": v for s, v in bys.items()}))
        r = rows[-1]
        say(f"  {k:3s} {r['bets']:5d} bets  CLV {r['clv']:+.2f} [{r['clv_lo']:+.2f}]  win {r['win']:.1%}  Open {r['u_open']:+7.1f}u  DK close {r['u_close']:+7.1f}u ({r['roi_close']:+.1%})"
            f"  RMSE {r['rmse']:.2f}  by season " + " ".join(f"{s % 100:02d}:{v:+.1f}" for s, v in bys.items()))
R = pd.DataFrame(rows); say("\nWINNERS (highest CLV; within 0.10 -> more units at the DK close) and the pass rule:")
for mk, g in R.groupby("market"):
    g = g.sort_values("clv", ascending=False); top = g.iloc[0]; near = g[g.clv >= top.clv - 0.10]; w = near.sort_values("u_close", ascending=False).iloc[0]
    every = all(w[f"u_{s}"] > 0 for s in CS)
    passed = w.clv >= BE[mk] and w.clv_lo > 0 and w.u_open > 0 and w.roi_close > -0.02 and every
    say(f"  {mk}: winner {w.model} (CLV {w.clv:+.2f}, Open {w.u_open:+.1f}u, DK close {w.roi_close:+.1%}, every season positive at the Open: {every}) -> "
        f"{'PASS -> PROVISIONAL after Fable review' if passed else 'FAIL -> TEST record'}")
open(os.path.join(ROOT, SUB, "research", "tournament_output.txt"), "w").write("\n".join(out) + "\n")
