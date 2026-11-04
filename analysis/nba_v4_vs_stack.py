"""NBA totals: live v4 vs the stack on the same games, 2024-26 (pre-registered: research/tournament/NBA_V4_VS_STACK_PREREG.md, commit 1c4c82c).
Descriptive (already-seen seasons). Needs _tmp/old_sbr_preds_{2024,2025,2026}.csv (nba_tournament.py predict) for the stack-as-tested input.
  python analysis/nba_v4_vs_stack.py WORKDIR -> analysis/nba_v4_vs_stack_output.txt"""
import os, sys, io, contextlib, json
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
TESTS = (2024, 2025, 2026)
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
rng = np.random.default_rng(1103)

# ---- Model 1 with injuries, lag 1, at DraftKings openers (as analysis/lag_leak_test.py)
src = open(os.path.join(W, "nba_mixed_model.py")).read()
ns = {"__name__": "nm_lag"}
exec(compile(src.replace("past = L_all[L_all.date < d]", "past = L_all[L_all.date < d - pd.Timedelta(days=LAG_DAYS)]"), "nm_lag", "exec"), ns)
ns["LAG_DAYS"] = 1
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"))
dk = O[O.book == "draftkings"][["date", "home", "away", "open_spread", "open_total", "close_total"]].drop_duplicates(["date", "home", "away"])
T = T.drop(columns=["open_spread", "open_total"]).merge(dk, on=["date", "home", "away"], how="left")
R = []
for test in TESTS:
    train = [s for s in range(2022, test)]
    with contextlib.redirect_stdout(io.StringIO()):
        _, P = ns["run"](T[T.season.isin(train + [test])], train, test, today_suffix="_open")
    R.append(P.assign(season=test)); print("Model 1", test, flush=True)
P = pd.concat(R, ignore_index=True).dropna(subset=["open_total", "close_total", "home_pts"])
P["date"] = pd.to_datetime(P.date)

# ---- stack-as-tested input: Model 1 without injuries (tournament predictions)
NI = pd.concat([pd.read_csv(os.path.join(W, "_tmp", f"old_sbr_preds_{s}.csv")) for s in TESTS], ignore_index=True)
NI["date"] = pd.to_datetime(NI.date)
P = P.merge(NI[["date", "home", "away", "pred_total"]].rename(columns={"pred_total": "m1_noinj"}), on=["date", "home", "away"], how="left")

# ---- season-to-date features through two nights before (box scores: simple, form, n, rested; shots: luck)
TT = T.copy(); TT["date"] = pd.to_datetime(TT.date); TT = TT[TT.home_pts.notna()]
tp = pd.concat([TT[["season", "date", "home"]].rename(columns={"home": "team"}).assign(tp=TT.home_pts + TT.away_pts),
                TT[["season", "date", "away"]].rename(columns={"away": "team"}).assign(tp=TT.home_pts + TT.away_pts)]).sort_values("date")
H = {k: g for k, g in tp.groupby(["season", "team"])}
TG = pd.read_csv(os.path.join(W, "analysis", "shot_quality_team_games.csv.gz")); TG["date"] = pd.to_datetime(TG.date)
HL = {k: g.sort_values("date") for k, g in TG.groupby(["season", "team"])}
sched = set(zip(pd.concat([TT.home, TT.away]), pd.concat([TT.date, TT.date])))
def f(season, team, d):
    g = H.get((season, team)); g = g[g.date < d - pd.Timedelta(days=1)] if g is not None else None
    n = 0 if g is None else len(g)
    if not n: return 0, np.nan, np.nan, np.nan
    l = HL.get((season, team)); l = l[l.date < d - pd.Timedelta(days=1)] if l is not None else None
    luck = (l.luck.mean() + l.opp_luck.mean()) if l is not None and len(l) >= 5 else np.nan
    return n, g.tp.mean(), g.tp.tail(10).mean() - g.tp.mean(), luck
for side in ("home", "away"):
    F = [f(s, t, d) for s, t, d in zip(P.season, P[side], P.date)]
    for i, c in enumerate(("n", "avg", "f10", "luck")): P[f"{side}_{c}"] = [x[i] for x in F]
P = P[(P.home_n >= 10) & (P.away_n >= 10) & P.home_luck.notna() & P.away_luck.notna() & P.m1_noinj.notna()].copy()
P["L"] = P.home_luck + P.away_luck; P["Lc"] = P.L - P.groupby("date").L.transform("mean")
P["rested"] = [float(((h, d - pd.Timedelta(days=1)) not in sched) and ((a, d - pd.Timedelta(days=1)) not in sched)) for h, a, d in zip(P.home, P.away, P.date)]
P["alt"] = P.home.isin(["den", "utah"]).astype(float)
P["simple"] = (P.home_avg + P.away_avg) / 2; P["form"] = P.home_f10 + P.away_f10
P["y"] = P.home_pts + P.away_pts - P.open_total
P["move"] = P.close_total - P.open_total
ng = np.minimum(P.home_n, P.away_n)
P["v4"] = P.pred_total - 0.5 * P.Lc * ng / (ng + 15) + 0.20 * P.form + 3.8 * P.alt
say(f"games: {len(P)} (DraftKings 2024-26, both teams 10+ games, open+close, luck available); by season {P.season.value_counts().sort_index().to_dict()}")

cfg = json.load(open(os.path.join(W, "data", "stack_totals.json"))); b = cfg["coef"]; thr = cfg["edge_threshold"]
def stack(m1):
    return (b["intercept"] + b["model1_minus_line"] * (m1 - P.open_total) + b["simple_minus_line"] * (P.simple - P.open_total)
            + b["form"] * P.form + b["altitude"] * P.alt + b["rested"] * P.rested)
E = {"1 v4 (live), edge 3+": (P.v4 - P.open_total, 3.0), "2 stack as tested (no-injury Model 1)": (stack(P.m1_noinj), thr),
     "3 stack as recorded live (injury Model 1)": (stack(P.pred_total), thr)}
cols = lambda D, luck: np.column_stack([np.ones(len(D)), D.pred_total - D.open_total, D.simple - D.open_total, D.form, D.alt, D.rested] + ([D.Lc] if luck else []))
for lab, luck in (("4a stack refit LOSO, no luck", False), ("4 stack + luck refit LOSO", True)):
    e = pd.Series(np.nan, index=P.index); th = pd.Series(np.nan, index=P.index); coefs = {}
    for s in TESTS:
        tr, te = P.season != s, P.season == s
        X = cols(P[tr], luck); bb = np.linalg.lstsq(X, P.y[tr].values, rcond=None)[0]
        sd = np.std(P.y[tr].values - X @ bb, ddof=1); e[te] = cols(P[te], luck) @ bb; th[te] = 0.0597 * sd; coefs[s] = np.round(bb, 3).tolist()
    E[lab] = (e, th); say(f"{lab} coefficients by held-out season (intercept, M1-line, simple-line, form, alt, rested{', luck' if luck else ''}): {coefs}")

def boot(B, n=4000):
    g = B.groupby("date").u.agg(["sum", "count"]).values; k = len(g)
    r = np.array([(lambda i: g[i, 0].sum() / g[i, 1].sum())(rng.integers(0, k, k)) for _ in range(n)])
    return np.percentile(r, 5), np.percentile(r, 95)
say("\nBets at the DraftKings opener, -110, 1 unit (pushes dropped). CLV = points the total moved toward the bet by the close.")
picks = {}
for lab, (e, t) in E.items():
    m = e.abs() >= t; B = P[m].copy(); B["sg"] = np.sign(e[m]); B["r"] = B.sg * B.y; B = B[B.r != 0]
    B["u"] = np.where(B.r > 0, 100 / 110, -1.0); B["clv"] = B.sg * B.move; picks[lab] = B
    lo, hi = boot(B); d_mse = np.mean(P.y ** 2 - (P.y - e) ** 2)
    bys = " ".join(f"{str(s)[2:]}:{x.u.sum():+.1f}" for s, x in B.groupby("season"))
    say(f"  {lab:42s} {len(B):5d} bets {np.mean(B.u > 0):.1%} {B.u.sum():+7.1f}u ROI {B.u.mean():+.1%} [{lo:+.1%},{hi:+.1%}]  CLV {B.clv.mean():+.2f}"
        f"  overs {np.mean(B.sg > 0):.0%}  MSE gain vs opener {d_mse:+.2f}  by season {bys}")
say("\nSame-game overlap with v4")
k4 = {(r.date, r.home): r.sg for r in picks["1 v4 (live), edge 3+"].itertuples()}
for lab in list(E)[1:]:
    kb = {(r.date, r.home): r.sg for r in picks[lab].itertuples()}
    both = set(k4) & set(kb); same = sum(k4[x] == kb[x] for x in both)
    only = picks[lab][[(d, h) not in k4 for d, h in zip(picks[lab].date, picks[lab].home)]]
    say(f"  {lab:42s} both bet {len(both)} (same side {same}); its bets v4 did not make: {len(only)}, {only.u.sum():+.1f}u, CLV {only.clv.mean():+.2f}")
B4 = picks["1 v4 (live), edge 3+"]; ks = set(zip(picks["2 stack as tested (no-injury Model 1)"].date, picks["2 stack as tested (no-injury Model 1)"].home))
o4 = B4[[(d, h) not in ks for d, h in zip(B4.date, B4.home)]]
say(f"  v4 bets the tested stack did not make: {len(o4)}, {o4.u.sum():+.1f}u, CLV {o4.clv.mean():+.2f}")
e4, e4a = E["4 stack + luck refit LOSO"][0], E["4a stack refit LOSO, no luck"][0]
d = (P.y - e4a) ** 2 - (P.y - e4) ** 2; g = d.groupby(P.date).agg(["sum", "count"]).values; k = len(g)
bs = np.array([(lambda i: g[i, 0].sum() / g[i, 1].sum())(rng.integers(0, k, k)) for _ in range(4000)])
say(f"\nLuck added to the stack (4 vs 4a, leave-one-season-out): paired MSE gain {d.mean():+.3f} [{np.percentile(bs, 5):+.3f},{np.percentile(bs, 95):+.3f}]")
open(os.path.join(W, "analysis", "nba_v4_vs_stack_output.txt"), "w").write("\n".join(out) + "\n")
