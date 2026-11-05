"""NCAAM pre-registered backtest (ncaab/research/NCAAM_PREREG_2026-11-05.md). Model: ncaab/model.py, ridge 5, carryover 0.8,
no recency decay (chosen on 2022-23 results only: ncaab/research/tune_2022_23.csv).
  python ncaab/backtest.py WORKDIR -> ncaab/research/backtest_output.txt, ncaab/data/bets.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); D = os.path.join(W, "ncaab", "data")
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
rng = np.random.default_rng(1105)
P = pd.read_csv(os.path.join(D, "preds.csv"), low_memory=False); P["date"] = pd.to_datetime(P.date)
# games played so far this season by each team, before the date
long = pd.concat([P[["season", "date", "hk"]].rename(columns={"hk": "t"}), P[["season", "date", "ak"]].rename(columns={"ak": "t"})])
long = long.sort_values("date"); long["n"] = long.groupby(["season", "t"]).cumcount()
first = long.groupby(["season", "t", "date"]).n.min()
P["hn"] = [first.get((s, t, d), 0) for s, t, d in zip(P.season, P.hk, P.date)]
P["an"] = [first.get((s, t, d), 0) for s, t, d in zip(P.season, P.ak, P.date)]
ok = P.home_d1 & P.away_d1 & P.neutral_ok & (np.minimum(P.hn, P.an) >= 3) & P.pred_margin.notna()
P["M"] = P.home_pts - P.away_pts; P["TOT"] = P.home_pts + P.away_pts
def pay(px): px = np.where(pd.isna(px), -110, px); return np.where(px > 0, px / 100, 100 / np.abs(px))
MK = {"spread": dict(line=-P.open_spread, close=-P.dk_spread, model=P.pred_margin, res=P["M"], cpx_pos=P.dk_spread_px, cpx_neg=P.dk_spread_away_px),
      "total": dict(line=P.open_total, close=P.dk_total, model=P.pred_total, res=P["TOT"], cpx_pos=P.dk_over_px, cpx_neg=P.dk_under_px)}
# "line" for spreads = the home margin the line implies (= -home spread); positive edge -> bet home
def bets(mk, season, thr):
    m = MK[mk]; k = ok & (P.season.isin(season if isinstance(season, list) else [season])) & m["line"].notna() & m["close"].notna()
    e = m["model"] - m["line"]; k = k & (e.abs() >= thr)
    B = P[k].copy(); sg = np.sign(e[k]); B["sg"] = sg; B["edge"] = e[k]
    B["clv"] = sg * (m["close"][k] - m["line"][k])
    ro = sg * (m["res"][k] - m["line"][k]); B["u_open"] = np.where(ro > 0, 100 / 110, np.where(ro < 0, -1.0, 0.0))
    rc = sg * (m["res"][k] - m["close"][k]); px = np.where(sg > 0, m["cpx_pos"][k], m["cpx_neg"][k])
    B["u_close"] = np.where(rc > 0, pay(px), np.where(rc < 0, -1.0, 0.0)); B["win_open"] = ro > 0; B["push_open"] = ro == 0
    return B
def ci(B, col):
    g = B.groupby("date")[col].agg(["sum", "count"]).values; k = len(g)
    r = [g[i, 0].sum() / g[i, 1].sum() for i in (rng.integers(0, k, k) for _ in range(3000))]
    return np.percentile(r, 5), np.percentile(r, 95)
def line(B, lab, be):
    if not len(B): say(f"  {lab}: no bets"); return
    lo, hi = ci(B, "clv"); n = len(B); w = B.win_open.sum(); l = n - w - B.push_open.sum()
    bys = " ".join(f"{s % 100:02d}:{g.u_open.sum():+.1f}/{g.clv.mean():+.2f}" for s, g in B.groupby("season"))
    say(f"  {lab:26s} {n:5d} bets  CLV {B.clv.mean():+.2f} [{lo:+.2f},{hi:+.2f}] (break-even {be:.2f})  at Open {w}-{l} {w/(w+l):.1%} "
        f"{B.u_open.sum():+7.1f}u ({B.u_open.mean():+.1%})  at DK close {B.u_close.sum():+7.1f}u ({B.u_close.mean():+.1%})  by season u/CLV {bys}")
say("NCAAM pre-registered backtest. Bets at the Open (-110); CLV = Open -> DraftKings close toward the bet (points).")
say(f"eligible games with Open + DK close: by season {P[ok & P.open_spread.notna() & P.dk_spread.notna()].groupby('season').size().to_dict()}")
dec = {}
for mk in MK:
    m = MK[mk]; f = ok & (P.season == 2024) & m["close"].notna()
    sd = float(np.std(m["res"][f] - m["close"][f])); be = 0.0238 * sd * np.sqrt(2 * np.pi)
    say(f"\n{mk.upper()}: 2023-24 sd of result vs DK close {sd:.2f} -> break-even CLV {be:.2f}")
    chosen = None
    for thr in (2, 3, 4, 5, 6):
        B = bets(mk, 2024, thr); line(B, f"fit 2023-24, {thr}+", be)
        if chosen is None and len(B) and B.clv.mean() >= be: chosen = thr
    say(f"  chosen threshold: {chosen if chosen is not None else 'NONE -> market FAILS'}")
    if chosen is None: dec[mk] = "FAIL (no threshold reached break-even CLV in 2023-24)"; continue
    T = bets(mk, [2025, 2026], chosen); line(T, f"TEST 2024-26, {chosen}+", be)
    lo, _ = ci(T, "clv")
    passed = T.clv.mean() >= be and lo > 0 and T.u_open.sum() > 0
    dec[mk] = ("PASS" if passed else "FAIL") + f" (CLV {T.clv.mean():+.2f} vs {be:.2f}, CLV low {lo:+.2f}, units at Open {T.u_open.sum():+.1f})"
    T.assign(market=mk).to_csv(os.path.join(D, f"bets_{mk}.csv"), index=False)
    say("  descriptive (test seasons): ")
    for lab, g in (("  Nov-Dec", T[T.date.dt.month.isin([11, 12])]), ("  Jan-Apr", T[T.date.dt.month.isin([1, 2, 3, 4])]),
                   ("  conference games", T[T.conf_game.astype(str) == "True"]), ("  neutral sites", T[T.neutral.astype(str) == "True"]),
                   ("  favorite/over side", T[T.sg > 0]), ("  dog/under side", T[T.sg < 0])):
        line(g, lab, be)
say("\nDECISIONS (pre-registered rule):"); [say(f"  {k}: {v}") for k, v in dec.items()]
open(os.path.join(W, "ncaab", "research", "backtest_output.txt"), "w").write("\n".join(out) + "\n")
