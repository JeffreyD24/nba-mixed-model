"""Sharp money signals test (sharp/SHARP_PREREG_2026-11-05.md).  python sharp/signals_test.py WORKDIR -> sharp/signals_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
def load(sp):
    D = pd.read_csv(os.path.join(W, "sharp", "data", f"{sp}_splits.csv.gz"), low_memory=False)
    st = pd.to_datetime(D.start, utc=True).dt.tz_convert("America/New_York"); D["date"] = st.dt.date.astype(str)
    D["season"] = st.dt.year + (st.dt.month >= 8).astype(int)
    if sp in ("nfl", "ncaaf"): D["season"] = st.dt.year + (st.dt.month >= 3).astype(int) - 0   # football: season = year it starts (+1 label below)
    if sp in ("nfl", "ncaaf"): D["season"] = np.where(st.dt.month >= 3, st.dt.year, st.dt.year - 1) + 1
    D = D[D.home_pts.notna() & D.away_pts.notna()].copy()
    D["close_sp"] = D.dk_spread.fillna(D.cons_spread); D["close_tot"] = D.dk_total.fillna(D.cons_total)
    D["G_sp"] = D.spread_home_money - D.spread_home_public; D["G_tot"] = D.total_over_money - D.total_over_public
    return D
def zrate(r):
    r = r[r != 0]; n = len(r); p = (r > 0).mean() if n else np.nan; return n, p, (p - .5) / np.sqrt(.25 / n) if n else np.nan
DISC, HOLD = [2020, 2021, 2022, 2023], [2024, 2025, 2026]
say("Seasons are end-year labels (2024 = 2023-24); football: 2024 = the 2023 season. Pushes excluded. -110.")
for sp in ("nba", "nhl", "nfl", "ncaab", "ncaaf"):
    D = load(sp); say(f"\n================ {sp.upper()} ({len(D)} games, {D.G_sp.notna().sum()} with splits) ================")
    for mk in ("spread", "total"):
        if sp == "nhl" and mk == "spread": say("  spread: NHL puck lines (+/-1.5 at varied prices) skipped; see totals"); continue
        if mk == "spread":
            G = D.G_sp; res = D.home_pts - D.away_pts; opn, cls = D.open_spread, D.close_sp
            vs = lambda L: np.sign(res + L)                      # +1 home covers
            tick = D.spread_home_public; move = -(cls - opn)     # + = line moved toward home (home more favored)
            mv_thr = 1.0
        else:
            G = D.G_tot; res = D.home_pts + D.away_pts; opn, cls = D.open_total, D.close_tot
            vs = lambda L: np.sign(res - L); tick = D.total_over_public; move = cls - opn; mv_thr = 1.5
        side = np.where(G >= 10, 1, np.where(G <= -10, -1, 0))
        rlm = np.where((move >= mv_thr) & (tick < 50), 1, np.where((move <= -mv_thr) & (tick > 50), -1, 0))
        for lab, sig in (("sharp side (gap>=10)", side), ("reverse line move", rlm)):
            line = []
            for per, ss in (("disc", DISC), ("hold", HOLD)):
                k = (sig != 0) & D.season.isin(ss)
                n_o, p_o, _ = zrate((sig * vs(opn))[k & opn.notna()]); n_c, p_c, z_c = zrate((sig * vs(cls))[k & cls.notna()])
                line.append((per, n_o, p_o, n_c, p_c, z_c))
            d, h = line
            q = d[4] >= 0.524 and d[5] >= 2.0
            dec = ("holdout " + ("PASS" if (h[4] >= 0.524 and h[5] >= 1.65) else "FAIL")) if q else "not qualified"
            say(f"  {mk:6s} {lab:22s} vs OPENER (descriptive) disc {d[2]:.1%} ({d[1]}) hold {h[2]:.1%} ({h[1]}) | vs CLOSE disc {d[4]:.1%} ({d[3]}, z {d[5]:+.1f}) hold {h[4]:.1%} ({h[3]}, z {h[5]:+.1f}) -> {dec}")
        k = G.notna() & opn.notna() & cls.notna()
        say(f"  {mk:6s} corr(gap, open->close move) {np.corrcoef(G[k], move[k])[0, 1]:+.2f}  (n {k.sum()})")
# ---------------- Q3 / Q4: our models vs sharp money ----------------
say("\n================ Q3 / Q4: our models and sharp money (2023-26) ================")
def q3(lab, M, model, line, close, res, thr, G):
    e = model - line; b = M[(e.abs() >= thr) & line.notna() & close.notna()].index
    sg = np.sign(e[b]); agree = np.sign(G[b]) == sg; strong = G[b].abs() >= 10
    for nm, kk in (("sharps agree (gap>=10 same side)", strong & agree), ("sharps disagree (gap>=10 other side)", strong & ~agree), ("no strong signal", ~strong)):
        ii = b[kk.values]; ro = sg[kk.values] * (res[ii] - line[ii]); rc = sg[kk.values] * (res[ii] - close[ii])
        uo = ((ro > 0).sum() * 100 / 110 - (ro < 0).sum()); uc = ((rc > 0).sum() * 100 / 110 - (rc < 0).sum())
        say(f"  {lab:28s} {nm:38s} {len(ii):4d} bets  at opener {(ro > 0).sum() / max((ro != 0).sum(), 1):.1%} {uo:+6.1f}u  at close {(rc > 0).sum() / max((rc != 0).sum(), 1):.1%} {uc:+6.1f}u")
    k = M.index[model.notna() & close.notna() & G.notna()]
    X = np.column_stack([np.ones(len(k)), (model - close)[k], G[k]]); y = (res - close)[k].values
    bb, *_ = np.linalg.lstsq(X, y, rcond=None); r = y - X @ bb; s2 = r @ r / (len(y) - 3); se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    say(f"  {lab:28s} Q4 result-close = a + b(model-close) + c(gap): b {bb[1]:+.3f} (t {bb[1] / se[1]:+.1f}), c {bb[2]:+.4f} per gap point (t {bb[2] / se[2]:+.1f}), n {len(k)}")
A = load("nba"); A["k"] = A.date + "_" + A.home_pts.astype(int).astype(str) + "_" + A.away_pts.astype(int).astype(str)
V = pd.read_csv(os.path.join(W, "analysis", "threshold_sweep_2026-11-04", "nba_v4_preds.csv"))
V["k"] = V.date.astype(str).str[:10] + "_" + V.home_pts.astype(int).astype(str) + "_" + V.away_pts.astype(int).astype(str)
M = V.merge(A[["k", "G_tot", "G_sp"]].drop_duplicates("k"), on="k", how="inner")
say(f"NBA v4 totals matched to splits: {len(M)} of {len(V)}")
q3("NBA totals v4 (3+)", M, M.v4, M.open_total, M.close_total, M.home_pts + M.away_pts, 3, M.G_tot)
C = load("ncaab"); C["k"] = C.date + "_" + C.home_pts.astype(int).astype(str) + "_" + C.away_pts.astype(int).astype(str)
C2 = C.copy(); C2["k"] = C.date + "_" + C.away_pts.astype(int).astype(str) + "_" + C.home_pts.astype(int).astype(str); C2["G_sp"] = -C2.G_sp
T = pd.read_csv(os.path.join(W, "ncaab", "data", "three_targets_preds.csv"), low_memory=False); T = T[(T.season >= 2024) & (T.book == "DraftKings")].copy()
T["k"] = T.date.astype(str).str[:10] + "_" + T.home_pts.astype(int).astype(str) + "_" + T.away_pts.astype(int).astype(str)
both = pd.concat([C[["k", "G_tot", "G_sp"]], C2[["k", "G_tot", "G_sp"]]]).drop_duplicates("k", keep=False)
M = T.merge(both, on="k", how="inner"); M["ENS_m"] = -1.306 + 0.597 * M.M2_m - 0.019 * M.M8_m + 0.545 * M.MKT_m
say(f"NCAAM DraftKings-opener games matched to splits: {len(M)} of {len(T)}")
q3("NCAAM totals M2 (6+)", M, M.M2_t, M.book_tot, M.close_tot, M.home_pts + M.away_pts, 6, M.G_tot)
q3("NCAAM spreads ENS (5+)", M, M.ENS_m, -M.book_sp, -M.close_sp, M.home_pts - M.away_pts, 5, M.G_sp)
open(os.path.join(W, "sharp", "signals_output.txt"), "w").write("\n".join(out) + "\n")
