"""Grade the NCAAM Model 2 tournament (ncaab/research/MODEL2_PREREG_2026-11-05.md). Needs ncaab/data/model2_preds.csv.
  python ncaab/model2_grade.py WORKDIR -> ncaab/research/model2_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
P = pd.read_csv(os.path.join(W, "ncaab", "data", "model2_preds.csv"), low_memory=False); P["date"] = pd.to_datetime(P.date)
long = pd.concat([P[["season", "date", "hk"]].rename(columns={"hk": "t"}), P[["season", "date", "ak"]].rename(columns={"ak": "t"})]).sort_values("date")
long["n"] = long.groupby(["season", "t"]).cumcount(); fg = long.groupby(["season", "t", "date"]).n.min()
P["hn"] = [fg.get((s, t, d), 0) for s, t, d in zip(P.season, P.hk, P.date)]; P["an"] = [fg.get((s, t, d), 0) for s, t, d in zip(P.season, P.ak, P.date)]
ok = (P.hk != "OTHER") & (P.ak != "OTHER") & (np.minimum(P.hn, P.an) >= 3)
P["nd_nc"] = P.date.dt.month.isin([11, 12]) & ~P.conf_game
FIT, TEST, DKS = [2012, 2013, 2014, 2015], [2016, 2017, 2018, 2019, 2020, 2021], [2024, 2025, 2026]
MODELS = ["M1", "M2", "M4", "M8", "M10"]
mk_cols = {"spread": dict(res=P.home_pts - P.away_pts, open=-P.open_sp, close=-P.close_sp, book=-P.book_sp, suf="m"),
           "total": dict(res=P.home_pts + P.away_pts, open=P.open_tot, close=P.close_tot, book=P.book_tot, suf="t")}
# ---- best rating model by tuning-season error feeds the stack
tune = P.season.isin([2009, 2010, 2011]) & ok
sc = {k: np.mean((mk_cols["spread"]["res"] - P[f"{k}_m"])[tune] ** 2) / 1 + 0 for k in MODELS}
st = {k: np.mean((mk_cols["total"]["res"] - P[f"{k}_t"])[tune] ** 2) for k in MODELS}
score = {k: sc[k] / min(sc.values()) + st[k] / min(st.values()) for k in MODELS}; base = min(score, key=score.get)
say(f"tuning-season error (2009-11): " + ", ".join(f"{k} margin MSE {sc[k]:.1f} total MSE {st[k]:.1f}" for k in MODELS) + f" -> stack base {base}")
# ---- stack: fair = open + sum b_k (model - open) x group_k, expanding window by season (fit on earlier seasons only)
for mk, c in mk_cols.items():
    e = P[f"{base}_{c['suf']}"] - c["open"]; X = np.column_stack([e, e * P.conf_game, e * P.both_power, e * P.nd_nc]); y = (c["res"] - c["open"]).values
    fair = np.full(len(P), np.nan); coefs = {}
    for s in range(2012, 2028):
        tr = (P.season < s) & ok & c["open"].notna() & ~np.isnan(X).any(axis=1); te = (P.season == s) & c["open"].notna()
        if tr.sum() < 1000: continue
        b = np.linalg.lstsq(X[tr.values], y[tr.values], rcond=None)[0]; coefs[s] = np.round(b, 3).tolist()
        fair[te.values] = c["open"][te].values + X[te.values] @ b
    P[f"STACK_{c['suf']}"] = fair
    say(f"stack {mk} coefficients (all, x conf game, x both power, x Nov-Dec non-conf) by season fitted: {coefs.get(2016)} (for 2016), {coefs.get(2022)} (for 2022)")
ENT = MODELS + ["STACK"]
rng = np.random.default_rng(55)
def grade(mk, k, seasons, thr, line_key="open"):
    c = mk_cols[mk]; line, close, res, mod = c[line_key], c["close"], c["res"], P[f"{k}_{c['suf']}"]
    sel = ok & P.season.isin(seasons) & line.notna() & close.notna() & mod.notna()
    e = mod - line; b = sel & (e.abs() >= thr)
    sg = np.sign(e[b]); clv = sg * (close[b] - line[b]); ro = sg * (res[b] - line[b]); rc = sg * (res[b] - close[b])
    uo = np.where(ro > 0, 100 / 110, np.where(ro < 0, -1.0, 0.0)); uc = np.where(rc > 0, 100 / 110, np.where(rc < 0, -1.0, 0.0))
    g = pd.DataFrame(dict(d=P.date[b].values, c=clv.values)).groupby("d").c.agg(["sum", "count"]).values
    lo = np.percentile([g[i, 0].sum() / g[i, 1].sum() for i in (rng.integers(0, len(g), len(g)) for _ in range(1000))], 5) if len(g) > 5 else np.nan
    # accuracy and beat-the-close on all eligible games
    rm = np.sqrt(np.mean((res[sel] - mod[sel]) ** 2)); x = (mod - close)[sel]; y = (res - close)[sel]
    sl = np.polyfit(x, y, 1)[0]; se = np.std(y - sl * x) / np.sqrt(((x - x.mean()) ** 2).sum())
    cap = clv.mean() / e[b].abs().mean() if b.sum() else np.nan
    bys = {s: float(uo[(P.season[b] == s).values].sum()) for s in seasons}
    return dict(n=int(b.sum()), win=np.mean(ro[ro != 0] > 0) if b.sum() else np.nan, u_open=uo.sum(), clv=clv.mean(), clv_lo=lo, u_close=uc.sum(),
                roi_close=uc.mean() if b.sum() else np.nan, rmse=rm, slope=sl, t=sl / se, capture=cap, bys=bys)
for mk, c in mk_cols.items():
    fitsel = ok & P.season.isin(FIT) & c["close"].notna()
    be = 0.0238 * np.std((c["res"] - c["close"])[fitsel]) * np.sqrt(2 * np.pi)
    tsel = ok & P.season.isin(TEST) & c["open"].notna() & c["close"].notna()
    say(f"\n===== {mk.upper()}  break-even CLV {be:.2f}  | books' numbers as predictors, test 2016-21: opener RMSE {np.sqrt(np.mean((c['res'] - c['open'])[tsel] ** 2)):.2f}, close RMSE {np.sqrt(np.mean((c['res'] - c['close'])[tsel] ** 2)):.2f}")
    rows = []
    for k in ENT:
        grid = (0.5, 1, 1.5, 2, 3) if k == "STACK" else (2, 3, 4, 5, 6)
        thr = next((t for t in grid if grade(mk, k, FIT, t)["clv"] >= be), None)
        if thr is None: say(f"  {k:6s} no threshold reached break-even CLV in 2012-15 -> FAIL"); continue
        r = grade(mk, k, TEST, thr); r.update(model=k, thr=thr); rows.append(r)
        d = grade(mk, k, DKS, thr, "book")
        say(f"  {k:6s} thr {thr:<4} TEST {r['n']:5d} bets {r['win']:.1%} open {r['u_open']:+7.1f}u CLV {r['clv']:+.2f} [{r['clv_lo']:+.2f}] close {r['u_close']:+7.1f}u ({r['roi_close']:+.1%})"
            f" | RMSE {r['rmse']:.2f} beat-close slope {r['slope']:+.3f} (t {r['t']:+.1f}) capture {r['capture']:.0%} | seasons " + " ".join(f"{s % 100:02d}:{v:+.0f}" for s, v in r["bys"].items())
            + f" || DK-own-opener 2024-26: {d['n']} bets {d['win']:.1%} {d['u_open']:+.1f}u CLV {d['clv']:+.2f}")
        r["dk"] = d
    if not rows: continue
    R = pd.DataFrame(rows).sort_values("clv", ascending=False); top = R.iloc[0]; near = R[R.clv >= top.clv - 0.10]; w = near.sort_values("u_close", ascending=False).iloc[0]
    passed = w.clv >= be and w.clv_lo > 0 and w.u_open > 0 and w.roi_close > -0.02 and w.dk["u_open"] > 0 and w.dk["clv"] >= be
    say(f"  WINNER {w.model} -> {'PASS -> PROVISIONAL after Fable review' if passed else 'FAIL -> TEST record'}"
        f" (CLV {w.clv:+.2f} vs {be:.2f}, low {w.clv_lo:+.2f}, open {w.u_open:+.1f}u, close ROI {w.roi_close:+.1%}, DK opener {w.dk['u_open']:+.1f}u CLV {w.dk['clv']:+.2f})")
open(os.path.join(W, "ncaab", "research", "model2_output.txt"), "w").write("\n".join(out) + "\n")
