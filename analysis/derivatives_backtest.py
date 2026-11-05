"""NBA 1st-half / 1st-quarter / team-total lines from our full-game models — backtest as pre-registered in
research/derivatives/DERIVATIVES_PREREG_2026-11-04.md (pushed before any results).
Inputs: data/period_history (Action Network: Open, DraftKings, FanDuel), _tmp/deriv_v4_preds.csv (analysis/derivatives_preds.py),
analysis/spreads_step1_nba_bets.csv (variant B = honest spread v2 model margin).
  python analysis/derivatives_backtest.py WORKDIR -> analysis/derivatives_backtest_output.txt, analysis/derivatives_bets.csv.gz"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
rng = np.random.default_rng(1104)
FIT, TEST = [2024], [2025, 2026]     # 2022-23 has no DraftKings period lines -> fit on 2023-24 only (pre-registered fallback)
K = 20

L = pd.read_csv(os.path.join(W, "data", "period_history", "nba_period_lines.csv.gz"))
S = pd.read_csv(os.path.join(W, "data", "period_history", "nba_linescores.csv"))
for c in ("home", "away"):
    S[f"{c}_h1"] = S[f"{c}_q1"] + S[f"{c}_q2"]
S["d"] = pd.to_datetime(S.date); S["season"] = S.d.dt.year + (S.d.dt.month >= 8)
S["full_m"] = S.home_final - S.away_final; S["full_t"] = S.home_final + S.away_final
S["h1_m"] = S.home_h1 - S.away_h1; S["h1_t"] = S.home_h1 + S.away_h1
S["q1_m"] = S.home_q1 - S.away_q1; S["q1_t"] = S.home_q1 + S.away_q1

# ---- model numbers
V = pd.read_csv(os.path.join(W, "_tmp", "deriv_v4_preds.csv"))
B = pd.read_csv(os.path.join(W, "analysis", "spreads_step1_nba_bets.csv")); B = B[B.variant == "B"][["date", "home", "away", "sp_model"]].drop_duplicates(["date", "home", "away"])
G = S.merge(V[["date", "home", "away", "v4"]], on=["date", "home", "away"], how="left").merge(B, on=["date", "home", "away"], how="left")
say(f"games with quarter scores: {len(S)}; with v4 total: {G.v4.notna().sum()}; with spread model: {G.sp_model.notna().sum()}")

# ---- shares (fit seasons only): margin = slope through origin; total = ratio of means
F = G[G.season.isin(FIT)]
sh = {"h1_m": (F.h1_m * F.full_m).sum() / (F.full_m ** 2).sum(), "q1_m": (F.q1_m * F.full_m).sum() / (F.full_m ** 2).sum(),
      "h1_t": F.h1_t.mean() / F.full_t.mean(), "q1_t": F.q1_t.mean() / F.full_t.mean()}
say("league shares (fit 2023-24): " + ", ".join(f"{k} {v:.4f}" for k, v in sh.items()))

# team start-of-game adjustments, shrunk with k=20, fit seasons only
adj = {}
for k in ("h1", "q1"):
    rm = F[f"{k}_m"] - sh[f"{k}_m"] * F.full_m; rt = F[f"{k}_t"] - sh[f"{k}_t"] * F.full_t
    R = pd.concat([pd.DataFrame(dict(team=F.home, m=rm, t=rt)), pd.DataFrame(dict(team=F.away, m=-rm, t=rt))])
    g = R.groupby("team").agg(sm=("m", "sum"), st=("t", "sum"), n=("m", "size"))
    adj[k] = dict(m=(g.sm / (g.n + K)).to_dict(), t=(g.st / (g.n + K)).to_dict())
    say(f"{k} team adjustments: margin range {min(adj[k]['m'].values()):+.2f}..{max(adj[k]['m'].values()):+.2f}, "
        f"total range {min(adj[k]['t'].values()):+.2f}..{max(adj[k]['t'].values()):+.2f}")
for k in ("h1", "q1"):
    G[f"{k}_pm"] = sh[f"{k}_m"] * G.sp_model + G.home.map(adj[k]["m"]).fillna(0) - G.away.map(adj[k]["m"]).fillna(0)
    G[f"{k}_pt"] = sh[f"{k}_t"] * G.v4 + G.home.map(adj[k]["t"]).fillna(0) + G.away.map(adj[k]["t"]).fillna(0)
G["home_tt_p"] = (G.v4 + G.sp_model) / 2; G["away_tt_p"] = (G.v4 - G.sp_model) / 2

# ---- lines: Open (bet line) and DraftKings (close)
def book(per, b):
    x = L[(L.period == per) & (L.book == b)].drop_duplicates(["date", "home", "away"], keep="last").set_index(["date", "home", "away"])
    return x
def dec(a): return np.where(a > 0, 1 + a / 100, 1 + 100 / np.abs(a))
def pay(a): a = pd.Series(a).fillna(-110).values; return dec(a) - 1

markets = []   # (name, period, threshold, model col, kind, line col at book, actual col, side cols)
markets += [("1H spread", "firsthalf", 1.5, "h1_pm", "spread", "h1_m"), ("1H total", "firsthalf", 2.0, "h1_pt", "total", "h1_t"),
            ("1Q spread", "firstquarter", 1.0, "q1_pm", "spread", "q1_m"), ("1Q total", "firstquarter", 1.0, "q1_pt", "total", "q1_t")]
rows = []
key = ["date", "home", "away"]
for name, per, thr, mc, kind, act in markets:
    O, D = book(per, "Open"), book(per, "DraftKings")
    X = G.set_index(key).join(O.add_prefix("o_"), how="inner").join(D.add_prefix("c_"), how="inner").reset_index()
    X = X[X[mc].notna()]
    if kind == "spread":
        X = X[X.o_home_spread.notna() & X.c_home_spread.notna()]
        e = X[mc] + X.o_home_spread; s = np.sign(e)
        X = X.assign(edge=e, side=np.where(s > 0, "home", "away"))
        X["res_o"] = s * (X[act] + X.o_home_spread); X["res_c"] = s * (X[act] + X.c_home_spread)
        X["clv"] = np.where(s > 0, X.o_home_spread - X.c_home_spread, X.c_home_spread - X.o_home_spread)
        X["pr_o"] = np.where(s > 0, X.o_home_spread_odds, X.o_away_spread_odds); X["pr_c"] = np.where(s > 0, X.c_home_spread_odds, X.c_away_spread_odds)
    else:
        X = X[X.o_total.notna() & X.c_total.notna()]
        e = X[mc] - X.o_total; s = np.sign(e)
        X = X.assign(edge=e, side=np.where(s > 0, "over", "under"))
        X["res_o"] = s * (X[act] - X.o_total); X["res_c"] = s * (X[act] - X.c_total)
        X["clv"] = s * (X.c_total - X.o_total)
        X["pr_o"] = np.where(s > 0, X.o_over_odds, X.o_under_odds); X["pr_c"] = np.where(s > 0, X.c_over_odds, X.c_under_odds)
    X["market"] = name; X["thr"] = thr
    rows.append(X[["date", "season", "home", "away", "market", "thr", "edge", "side", "res_o", "res_c", "clv", "pr_o", "pr_c"]])

# team totals (full game): Open team total vs model
O, D = book("game", "Open"), book("game", "DraftKings")
X = G.set_index(key).join(O.add_prefix("o_"), how="inner").join(D.add_prefix("c_"), how="inner").reset_index()
for side in ("home", "away"):
    Y = X[X[f"{side}_tt_p"].notna() & X[f"o_{side}_team_total"].notna() & X[f"c_{side}_team_total"].notna()].copy()
    e = Y[f"{side}_tt_p"] - Y[f"o_{side}_team_total"]; s = np.sign(e)
    act = Y[f"{side}_final"]
    Y = Y.assign(edge=e, side=np.where(s > 0, f"{side} over", f"{side} under"), market="Team total", thr=2.0)
    Y["res_o"] = s * (act - Y[f"o_{side}_team_total"]); Y["res_c"] = s * (act - Y[f"c_{side}_team_total"])
    Y["clv"] = s * (Y[f"c_{side}_team_total"] - Y[f"o_{side}_team_total"])
    Y["pr_o"] = np.where(s > 0, Y[f"o_{side}_tt_over"], Y[f"o_{side}_tt_under"]); Y["pr_c"] = np.where(s > 0, Y[f"c_{side}_tt_over"], Y[f"c_{side}_tt_under"])
    rows.append(Y[["date", "season", "home", "away", "market", "thr", "edge", "side", "res_o", "res_c", "clv", "pr_o", "pr_c"]])

A = pd.concat(rows, ignore_index=True)
A["bet"] = A.edge.abs() >= A.thr
A["u_o"] = np.where(A.res_o > 0, pay(A.pr_o), np.where(A.res_o < 0, -1.0, 0.0))
A["u_c"] = np.where(A.res_c > 0, pay(A.pr_c), np.where(A.res_c < 0, -1.0, 0.0))
A.to_csv(os.path.join(W, "analysis", "derivatives_bets.csv.gz"), index=False)

def boot_ci(Bt, col, n=4000):
    g = Bt.groupby("date")[col].agg(["sum", "count"]).values
    if len(g) < 5: return np.nan, np.nan
    idx = rng.integers(0, len(g), (n, len(g))); m = g[idx, 0].sum(1) / g[idx, 1].sum(1)
    return np.percentile(m, 5), np.percentile(m, 95)

def summary(Bt):
    wo = Bt[Bt.res_o != 0]; wc = Bt[Bt.res_c != 0]
    lo, hi = boot_ci(Bt, "clv"); ulo, uhi = boot_ci(Bt, "u_c")
    return (f"{len(Bt):5d} bets | CLV {Bt.clv.mean():+.2f} [{lo:+.2f}, {hi:+.2f}] | at DK close: {(wc.res_c > 0).mean()*100:5.1f}% "
            f"{Bt.u_c.sum():+7.1f}u ({Bt.u_c.mean()*100:+.1f}% [{ulo*100:+.1f}, {uhi*100:+.1f}]) | at Open: {(wo.res_o > 0).mean()*100:5.1f}% {Bt.u_o.sum():+7.1f}u")

say("\n== TEST seasons 2024-25 + 2025-26 (pre-registered thresholds) ==")
verdict = {}
for m in ["1H spread", "1H total", "1Q spread", "1Q total", "Team total"]:
    Bt = A[(A.market == m) & A.bet & A.season.isin(TEST)]
    if not len(Bt): say(f"{m:11s}: no bets"); continue
    lo, _ = boot_ci(Bt, "clv")
    passed = (lo > 0) and Bt.u_c.sum() > 0
    verdict[m] = passed
    say(f"{m:11s}: {summary(Bt)} -> {'PASS' if passed else 'fail'}")
    for s in TEST:
        b = Bt[Bt.season == s]; say(f"      {s}: {len(b)} bets, CLV {b.clv.mean():+.2f}, DK close {b.u_c.sum():+.1f}u, Open {b.u_o.sum():+.1f}u")
say("\n== FIT season 2023-24 (in-sample, for reference only) ==")
for m in ["1H spread", "1H total", "1Q spread", "1Q total", "Team total"]:
    Bt = A[(A.market == m) & A.bet & A.season.isin(FIT)]
    if len(Bt): say(f"{m:11s}: {summary(Bt)}")
say("\n== Direction check (test seasons): overs/home vs unders/away ==")
for m in ["1H total", "1Q total", "Team total", "1H spread", "1Q spread"]:
    Bt = A[(A.market == m) & A.bet & A.season.isin(TEST)]
    if len(Bt): say(f"{m:11s}: " + "; ".join(f"{k} {len(g)} bets CLV {g.clv.mean():+.2f} {g.u_c.sum():+.1f}u" for k, g in Bt.assign(k=Bt.side.str.extract(r'(over|under|home|away)')[0]).groupby("k")))

# ---- side questions
say("\n== How mechanical are DraftKings' derived lines? (all seasons with DK) ==")
Dg = book("game", "DraftKings")
for per, lab in (("firsthalf", "1H"), ("firstquarter", "1Q")):
    Dp = book(per, "DraftKings")
    J = Dg[["home_spread", "total"]].join(Dp[["home_spread", "total"]], rsuffix="_p", how="inner").dropna().reset_index().merge(S, on=key)
    for a, b, act, full in (("home_spread", "home_spread_p", f"{'h1' if lab=='1H' else 'q1'}_m", "spread"), ("total", "total_p", f"{'h1' if lab=='1H' else 'q1'}_t", "total")):
        bb = np.polyfit(J[a], J[b], 1); fit = np.polyval(bb, J[a]); res = J[b] - fit
        r2 = 1 - res.var() / J[b].var()
        # does the gap (period line vs its usual fraction of the full line) predict the period result relative to the period line?
        y = (J[act] + J[b]) if full == "spread" else (J[act] - J[b])        # spread: positive = home covers; total: positive = over
        c = np.corrcoef(res, y)[0, 1]
        say(f"{lab} {full}: DK {lab} line = {bb[0]:.3f} x full line {bb[1]:+.2f}; R² {r2:.3f}; leftover sd {res.std():.2f} pts; "
            f"corr(leftover, result vs {lab} line) {c:+.3f} (n {len(J)})")

say("\n== Verdict ==")
for m, p in verdict.items(): say(f"{m}: {'PASS -> PROVISIONAL live after the Fable check' if p else 'did not pass'}")
open(os.path.join(W, "analysis", "derivatives_backtest_output.txt"), "w").write("\n".join(out) + "\n")
