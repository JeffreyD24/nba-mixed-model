"""Bail-out test (Nov 4, 2026). Pre-registered in analysis/BAILOUT_PREREG.md (commit f8364f0) before any result.
Opener bets with edge 3+ (DraftKings 2023-26, analysis/line_move_threshold_bets.csv). Walk the DraftKings snapshots; at the FIRST snapshot
the line is k+ pts against the bet line (k = 1, 2, 3, 4), compare riding the bet with hedging (1 unit the other side at that line, -110).
The average ride return per unit staked at that moment is the break-even cash-out offer.
  python analysis/bailout_test.py WORKDIR -> analysis/bailout_test_output.txt, analysis/bailout_thresholds.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
rng = np.random.default_rng(7)
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

B = pd.read_csv(os.path.join(W, "analysis", "line_move_threshold_bets.csv"))
key = ["date", "home", "away"]
S = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_snapshots.csv.gz"), usecols=key + ["t", "tip", "book", "tot", "sp"])
S = S[S.book == "draftkings"].copy()
S["t"] = pd.to_datetime(S.t, utc=True); S["tip"] = pd.to_datetime(S.tip, utc=True)
S = S[S.t < S.tip].sort_values("t")
PATH = {("total", k): g.tot.dropna().values for k, g in S.groupby(key)}
PATH.update({("spread", k): g.sp.dropna().values for k, g in S.groupby(key)})

WIN = 1 + 100 / 110
def ret(x):            # return per unit staked at -110 for a margin x vs the line (x>0 win, 0 push)
    return np.where(x > 0, WIN, np.where(x == 0, 1.0, 0.0))

rows = []
for r in B.itertuples(index=False):
    p = PATH.get((r.market, (r.date, r.home, r.away)))
    if p is None or len(p) == 0 or pd.isna(r.open_res): continue
    s = r.side
    if r.market == "total":
        act = r.open + s * r.open_res; tow = s * (p - r.open)
        hedge = lambda L: -s * (act - L)
    else:
        mg = s * r.open_res - r.open; tow = -s * (p - r.open)
        hedge = lambda L: -s * (mg + L)
    for k in (1, 2, 3, 4):
        hit = np.where(tow <= -k + 0.01)[0]
        if not len(hit): continue
        L = p[hit[0]]
        rows.append(dict(market=r.market, season=r.season, k=k, ride_x=r.open_res, hedge_x=hedge(L), trig_line=L, open=r.open))
X = pd.DataFrame(rows)
X["ride_ret"] = ret(X.ride_x); X["hedge_ret"] = ret(X.hedge_x)

def wr(x):
    x = np.asarray(x); w, l = (x > 0).sum(), (x < 0).sum(); return w / max(w + l, 1), int(w), int(l)
def boot_wr(x, n=2000):
    x = np.asarray(x); x = x[x != 0]
    if len(x) < 5: return (np.nan, np.nan)
    b = [(rng.choice(x, len(x)) > 0).mean() for _ in range(n)]; return tuple(np.percentile(b, [5, 95]))

thr = []
for mk in ("total", "spread"):
    say(f"\n==== NBA {mk.upper()}S: opener bets (edge 3+) whose DraftKings line later moved k+ pts against, DK 2023-26 ====")
    n_bets = int((B.market == mk).sum())
    say(f"opener bets: {n_bets}")
    say(f"{'k':>3} {'trig':>5} | {'ride W-L':>9} {'win%':>6} {'90% int':>13} | {'cash-out break-even':>20} | {'hedge bet W-L':>13} {'win%':>6} | by season (ride win%, n)")
    chosen = None
    for k in (1, 2, 3, 4):
        D = X[(X.market == mk) & (X.k == k)]
        if not len(D): continue
        w, a, b = wr(D.ride_x); lo, hi = boot_wr(D.ride_x); be = D.ride_ret.mean()
        hw, ha, hb = wr(D.hedge_x)
        bys, ok_seasons, hed_seasons = [], 0, 0
        for se in (2024, 2025, 2026):
            d = D[D.season == se]; sw = wr(d.ride_x); hs = wr(d.hedge_x)
            bys.append(f"{se % 100}: {sw[0]:.0%} ({sw[1] + sw[2]})"); ok_seasons += sw[0] < 110 / 210 and (sw[1] + sw[2]) > 0
            hed_seasons += hs[0] >= 110 / 210
        say(f"{k:>3} {len(D):>5} | {a:>4}-{b:<4} {w:6.1%} {lo:6.1%}-{hi:5.1%} | {be:>8.3f} per unit       | {ha:>6}-{hb:<6} {hw:6.1%} | {', '.join(bys)}")
        qual = (w < 0.476) and (a + b >= 60) and (ok_seasons >= 2)
        hedge_ok = (hw >= 110 / 210) and (hed_seasons >= 2)
        if qual and chosen is None: chosen = k
        thr.append(dict(market=mk, k=k, n=len(D), p_win=round(float((D.ride_x > 0).mean()), 4), p_push=round(float((D.ride_x == 0).mean()), 4), ride_win=round(w, 4), ci_lo=round(lo, 4), ci_hi=round(hi, 4), breakeven_per_unit=round(be, 4),
                        hedge_win=round(hw, 4), qualifies=bool(qual), hedge_ok=bool(hedge_ok), seasons_below=int(ok_seasons)))
    say(f"  -> pre-registered rule: alert from k = {chosen} pts" if chosen else "  -> pre-registered rule: no k qualifies, no bail-out alert for this market")
    for t in thr:
        if t["market"] == mk and chosen and t["k"] >= chosen:
            t["alert"] = True
T = pd.DataFrame(thr)
LIVE = {("total", 3), ("total", 4), ("spread", 1), ("spread", 2)}      # tiers used by bailout.py (spread 3-4: under 30 bets)
T["alert"] = [(m, k) in LIVE for m, k in zip(T.market, T.k)]
T.to_csv(os.path.join(W, "analysis", "bailout_thresholds.csv"), index=False)
say("\nReading the break-even: 1.909 per unit = a sure win, 1.0 = getting the stake back. For a $2.50 bet at -110, cash out only if offered")
say("at least 2.50 x break-even; below that, riding has been worth more on average.")
open(os.path.join(W, "analysis", "bailout_test_output.txt"), "w").write("\n".join(out) + "\n")
