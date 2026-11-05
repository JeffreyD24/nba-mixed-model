"""Grade the NCAAM three-target tournament (ncaab/research/THREE_TARGETS_PREREG_2026-11-05.md).
  python ncaab/three_targets_grade.py WORKDIR -> ncaab/research/three_targets_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
P = pd.read_csv(os.path.join(W, "ncaab", "data", "three_targets_preds.csv"), low_memory=False); P["date"] = pd.to_datetime(P.date)
long = pd.concat([P[["season", "date", "hk"]].rename(columns={"hk": "t"}), P[["season", "date", "ak"]].rename(columns={"ak": "t"})]).sort_values("date")
long["n"] = long.groupby(["season", "t"]).cumcount(); fg = long.groupby(["season", "t", "date"]).n.min()
P["hn"] = [fg.get((s, t, d), 0) for s, t, d in zip(P.season, P.hk, P.date)]; P["an"] = [fg.get((s, t, d), 0) for s, t, d in zip(P.season, P.ak, P.date)]
P["nd_nc"] = P.date.dt.month.isin([11, 12]) & ~P.conf_game.astype(bool)
base = (P.hk != "OTHER") & (P.ak != "OTHER") & (np.minimum(P.hn, P.an) >= 3) & P.book_sp.notna() & P.close_sp.notna() & P.book_tot.notna() & P.close_tot.notna()
base &= P[["M1_m", "M2_m", "M8_m", "MKT_m", "M1_t", "M2_t", "M8_t", "MKT_t"]].notna().all(axis=1)
FIT = base & (P.season == 2024) & (P.book == "DraftKings"); TEST = base & (P.season == 2026) & (P.book == "DraftKings"); EB = base & (P.season == 2025) & (P.book == "ESPN BET")
say(f"games: fit DK 2023-24 {FIT.sum()}, TEST DK 2025-26 {TEST.sum()}, ESPN BET 2024-25 {EB.sum()}")
rm = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
rng = np.random.default_rng(9)
for mk in ("spread", "total"):
    sfx = "m" if mk == "spread" else "t"
    res = (P.home_pts - P.away_pts) if mk == "spread" else (P.home_pts + P.away_pts)
    op = -P.book_sp if mk == "spread" else P.book_tot; cl = -P.close_sp if mk == "spread" else P.close_tot
    ents = {k: P[f"{k}_{sfx}"] for k in ("M1", "M2", "M8", "MKT")}
    Xf = lambda k: np.column_stack([np.ones(k.sum())] + [ents[e][k] for e in ("M2", "M8", "MKT")])
    b = np.linalg.lstsq(Xf(FIT), res[FIT], rcond=None)[0]; ents["ENS"] = pd.Series(np.nan, index=P.index); ents["ENS"][base] = Xf(base) @ b
    say(f"\n=================== {mk.upper()} ===================")
    say(f"A. RESULTS (RMSE vs actual, lower = better). ENS weights (const, M2, M8, MKT) fit 2023-24: {np.round(b, 3).tolist()}")
    for lab, kk in (("TEST DK 2025-26", TEST), ("ESPN BET 2024-25", EB)):
        say(f"  {lab}: " + "  ".join(f"{k} {rm(res[kk], v[kk]):.2f}" for k, v in ents.items()) + f"  | DK opener {rm(res[kk], op[kk]):.2f}  close {rm(res[kk], cl[kk]):.2f}")
    bo = np.linalg.lstsq(np.column_stack([np.ones(FIT.sum()), ents['MKT'][FIT], ents['M2'][FIT], ents['M8'][FIT]]), op[FIT], rcond=None)[0]
    OB = pd.Series(np.nan, index=P.index); OB[base] = np.column_stack([np.ones(base.sum()), ents['MKT'][base], ents['M2'][base], ents['M8'][base]]) @ bo
    say(f"B. DRAFTKINGS' OPENER (RMSE vs the opener). Blend (const, MKT, M2, M8) fit 2023-24: {np.round(bo, 3).tolist()}")
    for lab, kk in (("TEST DK 2025-26", TEST), ("ESPN BET 2024-25 opener", EB)):
        say(f"  {lab}: " + "  ".join(f"{k} {rm(op[kk], v[kk]):.2f}" for k, v in ents.items() if k != "ENS") + f"  BLEND {rm(op[kk], OB[kk]):.2f}")
    # C. close from the opener
    y = cl - op; d2, dk, d8 = ents["M2"] - op, ents["MKT"] - op, ents["M8"] - op
    g = [P.conf_game.astype(float), P.both_power.astype(float), P.nd_nc.astype(float)]
    FEAT = {"C1": [d2], "C2": [d2, dk], "C3": [d2, dk, d8], "C4": [d2, dk, d8] + [x * gg for x in (d2, dk, d8) for gg in g]}
    def X(name, k): return np.column_stack([np.ones(k.sum())] + [f[k] for f in FEAT[name]])
    cv = {}
    idx = np.where(FIT)[0]; folds = np.array_split(rng.permutation(len(idx)), 5)
    for name in FEAT:
        err = []
        for f in folds:
            tr = np.ones(len(idx), bool); tr[f] = False
            ktr = pd.Series(False, index=P.index); ktr.iloc[idx[tr]] = True; kte = pd.Series(False, index=P.index); kte.iloc[idx[f]] = True
            bb = np.linalg.lstsq(X(name, ktr), y[ktr], rcond=None)[0]; err.append(np.mean((y[kte] - X(name, kte) @ bb) ** 2))
        cv[name] = np.sqrt(np.mean(err))
    best = min(cv, key=cv.get)
    say(f"C. THE CLOSE (from DK's opener). 2023-24 cross-validated RMSE of close: C0 {np.sqrt(np.mean(y[FIT] ** 2)):.3f}  " + "  ".join(f"{k} {v:.3f}" for k, v in cv.items()) + f" -> chosen {best}")
    coef = {n: np.linalg.lstsq(X(n, FIT), y[FIT], rcond=None)[0] for n in FEAT}
    say(f"  {best} coefficients: {np.round(coef[best], 3).tolist()}")
    for lab, kk in (("TEST DK 2025-26", TEST), ("ESPN BET 2024-25", EB)):
        parts = [f"C0 {np.sqrt(np.mean(y[kk] ** 2)):.3f}"]
        for n in FEAT:
            pm = X(n, kk) @ coef[n]; parts.append(f"{n} {np.sqrt(np.mean((y[kk] - pm) ** 2)):.3f} (corr {np.corrcoef(pm, y[kk])[0, 1]:+.2f})")
        say(f"  {lab} RMSE vs close: " + "  ".join(parts))
    # betting rule
    BE = 0.63 if mk == "spread" else 1.02
    def bet(kk, k):
        pm = pd.Series(X(best, kk) @ coef[best], index=P.index[kk]); sel = pm.abs() >= k; ii = pm.index[sel]; sg = np.sign(pm[sel])
        clv = sg * (cl[ii] - op[ii]); ro = sg * (res[ii] - op[ii]); rc = sg * (res[ii] - cl[ii])
        uo = np.where(ro > 0, 100 / 110, np.where(ro < 0, -1.0, 0.0)); uc = np.where(rc > 0, 100 / 110, np.where(rc < 0, -1.0, 0.0))
        gg = pd.DataFrame(dict(d=P.date[ii].values, c=clv.values)).groupby("d").c.agg(["sum", "count"]).values
        lo = np.percentile([gg[i, 0].sum() / gg[i, 1].sum() for i in (rng.integers(0, len(gg), len(gg)) for _ in range(1000))], 5) if len(gg) > 5 else np.nan
        return len(ii), clv.mean(), lo, uo.sum(), uc.sum(), np.mean(ro[ro != 0] > 0) if len(ii) else np.nan
    kk_ = next((k for k in (0.5, 1, 1.5, 2) if bet(FIT, k)[1] >= BE), None)
    for k in (0.5, 1, 1.5, 2):
        n, c, lo, uo, uc, w = bet(FIT, k); say(f"  fit 2023-24 |pred move| >= {k}: {n} bets, CLV {c:+.2f}, open {uo:+.1f}u, close {uc:+.1f}u, win {w:.1%}")
    if kk_ is None: say(f"  RULE: no k reached break-even CLV {BE} in 2023-24 -> FAIL"); continue
    n, c, lo, uo, uc, w = bet(TEST, kk_); passed = c >= BE and lo > 0 and uo > 0
    say(f"  TEST 2025-26 at k {kk_}: {n} bets {w:.1%}, CLV {c:+.2f} [low {lo:+.2f}] vs {BE}, open {uo:+.1f}u, close {uc:+.1f}u -> {'PASS -> PROVISIONAL candidate (Fable first)' if passed else 'FAIL -> TEST record'}")
    n, c, lo, uo, uc, w = bet(EB, kk_); say(f"  (ESPN BET 2024-25, decides nothing): {n} bets {w:.1%}, CLV {c:+.2f}, open {uo:+.1f}u, close {uc:+.1f}u")
open(os.path.join(W, "ncaab", "research", "three_targets_output.txt"), "w").write("\n".join(out) + "\n")
