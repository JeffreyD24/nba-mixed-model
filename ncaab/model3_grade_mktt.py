"""Grade NCAAM Model 3 (ncaab/research/MODEL3_PREREG_2026-11-05.md).  python ncaab/model3_grade.py WORKDIR -> ncaab/research/model3_output_mktt.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
P = pd.read_csv(os.path.join(W, "ncaab", "data", "model3_preds.csv"), low_memory=False); P["date"] = pd.to_datetime(P.date)
long = pd.concat([P[["season", "date", "hk"]].rename(columns={"hk": "k"}), P[["season", "date", "ak"]].rename(columns={"ak": "k"})]).sort_values("date")
long["n"] = long.groupby(["season", "k"]).cumcount(); fg = long.groupby(["season", "k", "date"]).n.min()
P["hn"] = [fg.get((s, k, d), 0) for s, k, d in zip(P.season, P.hk, P.date)]; P["an"] = [fg.get((s, k, d), 0) for s, k, d in zip(P.season, P.ak, P.date)]
ok = (P.hk != "OTHER") & (P.ak != "OTHER") & (np.minimum(P.hn, P.an) >= 3)
sbr = P.season <= 2021; dk = P.book == "DraftKings"; eb = P.book == "ESPN BET"
rng = np.random.default_rng(7)
for mk in ("spread", "total"):
    sgn = -1 if mk == "spread" else 1; s_ = "m" if mk == "spread" else "t"
    res = (P.home_pts - P.away_pts) if mk == "spread" else (P.home_pts + P.away_pts)
    so, sc = sgn * (P.open_sp if mk == "spread" else P.open_tot), sgn * (P.close_sp if mk == "spread" else P.close_tot)
    sbr_ok = sbr & so.notna() & sc.notna() & ((so - sc).abs() < 6)
    dko = sgn * (P.book_sp if mk == "spread" else P.book_tot)                     # book's own opener (DK or ESPN BET), home-margin / total scale
    opener = pd.Series(np.where(sbr, so, dko), index=P.index); opener[sbr & ~sbr_ok] = np.nan
    close = pd.Series(np.where(sbr | (P.season >= 2024), sc, np.nan), index=P.index)  # 2022-23 consensus close was captured after tip: not used
    F = {k: P[f"{k}_{s_}"] for k in ("M2", "M8", "MKTT")}
    # stacks, expanding window by season: A -> result, B -> opener, C -> close (C also uses the opener)
    stacks = {}
    for tag, target, feats in (("BLEND-A", res, ["M2", "M8", "MKTT"]), ("BLEND-B", opener, ["M2", "M8", "MKTT"]), ("BLEND-C", close, ["M2", "M8", "MKTT", "OPEN"])):
        X = np.column_stack([np.ones(len(P))] + [(opener if f == "OPEN" else F[f]).values for f in feats]); y = target.values
        pred = np.full(len(P), np.nan); coef = {}
        for s in range(2012, 2028):
            tr = (P.season < s).values & ok.values & ~np.isnan(X).any(axis=1) & ~np.isnan(y)
            te = (P.season == s).values & ~np.isnan(X).any(axis=1)
            if tr.sum() < 2000: continue
            b = np.linalg.lstsq(X[tr], y[tr], rcond=None)[0]; pred[te] = X[te] @ b; coef[s] = np.round(b, 3)
        stacks[tag] = pd.Series(pred, index=P.index)
        say(f"{mk} {tag} coefficients for 2026 (const, {', '.join(feats)}): {coef.get(2026)}")
    rm = lambda a, b, k: np.sqrt(np.mean((a[k] - b[k]) ** 2))
    say(f"\n===== {mk.upper()} (decision rows: DraftKings 2023-24 + 2025-26; ESPN BET 2024-25 shown separately)")
    for lab, rows in (("DK 2024+2026", ok & dk & P.season.isin([2024, 2026])), ("ESPN BET 2025", ok & eb & (P.season == 2025)), ("SBR 2016-21", ok & sbr_ok & P.season.between(2016, 2021))):
        k = rows & opener.notna() & close.notna() & res.notna()
        for c in list(F.values()) + list(stacks.values()): k = k & c.notna()
        allp = {**F, **stacks}
        say(f"  [{lab}] n={int(k.sum())}")
        say("    A result RMSE : " + "  ".join(f"{n} {rm(res, p, k):.2f}" for n, p in allp.items()) + f"  | opener {rm(res, opener, k):.2f}  close {rm(res, close, k):.2f}")
        say("    B opener RMSE : " + "  ".join(f"{n} {rm(opener, p, k):.2f}" for n, p in allp.items()))
        mv = (close - opener)[k]
        r2 = lambda p: 1 - np.sum((mv - (p - opener)[k]) ** 2) / np.sum(mv ** 2)
        say("    C close RMSE  : " + "  ".join(f"{n} {rm(close, p, k):.2f}" for n, p in allp.items()) + f"  | opener {rm(close, opener, k):.2f}   move R2: " + "  ".join(f"{n} {r2(p):+.3f}" for n, p in allp.items()))
    # betting from BLEND-C: predicted move vs the opener
    be = 0.63 if mk == "spread" else 1.02; pc = stacks["BLEND-C"]; e = pc - opener
    def bets(rows, x):
        k = rows & ok & opener.notna() & close.notna() & pc.notna() & (e.abs() >= x)
        sg = np.sign(e[k]); clv = sg * (close[k] - opener[k]); r = sg * (res[k] - opener[k]); u = np.where(r > 0, 100 / 110, np.where(r < 0, -1.0, 0.0))
        return k, clv, r, u
    X = next((x for x in (0.5, 1, 1.5, 2, 3) if bets(sbr_ok & P.season.between(2016, 2021), x)[1].mean() >= be), None)
    say(f"  BET RULE: threshold chosen on SBR 2016-21 = {X}")
    if X is None: say("  -> no threshold reached break-even CLV on SBR 2016-21: FAIL"); continue
    for lab, rows in (("SBR 2016-21 (fit)", sbr_ok & P.season.between(2016, 2021)), ("DK 2024+2026 (DECIDES)", dk & P.season.isin([2024, 2026])), ("ESPN BET 2025", eb & (P.season == 2025))):
        k, clv, r, u = bets(rows, X); g = pd.DataFrame(dict(d=P.date[k].values, c=clv.values)).groupby("d").c.agg(["sum", "count"]).values
        lo = np.percentile([g[i, 0].sum() / g[i, 1].sum() for i in (rng.integers(0, len(g), len(g)) for _ in range(1000))], 5) if len(g) > 5 else np.nan
        w, l = (r > 0).sum(), (r < 0).sum(); verdict = ""
        if "DECIDES" in lab: verdict = " -> " + ("PASS (Fable review next)" if clv.mean() >= be and u.sum() > 0 and lo > 0 else "FAIL -> TEST record")
        say(f"  {lab:24s} {int(k.sum()):5d} bets {w / max(w + l, 1):.1%} {u.sum():+7.1f}u CLV {clv.mean():+.2f} [low {lo:+.2f}] (b/e {be}){verdict}")
open(os.path.join(W, "ncaab", "research", "model3_output_mktt.txt"), "w").write("\n".join(out) + "\n")
