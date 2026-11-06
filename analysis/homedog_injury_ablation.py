"""NBA spreads: is the 2023-26 home-underdog loss caused by the injury features? (Nov 6, 2026)

Pre-registered: betting-goals/models/tests/NBA_HOMEDOG_INJURY_ABLATION_PREREG.md (pushed 38579c4 before computing).
Model 1 walk-forward as analysis/rule_audit_injury_timing.py (lag 1, train 2022..test-1, test 2024-2026, 8 PM report = "_open"
columns), (a) with injury features, (b) with every injury column dropped. Edge 3+ at the DK opening spread, both teams 10+ games, -110.
  python analysis/homedog_injury_ablation.py .  -> analysis/homedog_injury_ablation_output.txt, analysis/homedog_injury_ablation_bets.csv"""
import os, sys, io, contextlib
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
sys.path.insert(0, W); os.chdir(W)
BOOT, SEED = 10000, 20261106
src = open(os.path.join(W, "nba_mixed_model.py")).read()
assert "past = L_all[L_all.date < d]" in src
ns = {"__name__": "nm_lag"}
exec(compile(src.replace("past = L_all[L_all.date < d]", "past = L_all[L_all.date < d - pd.Timedelta(days=LAG_DAYS)]"), "nm_lag", "exec"), ns)
ns["LAG_DAYS"] = 1

T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"))
dk = O[O.book == "draftkings"][["date", "home", "away", "open_spread", "open_total"]].drop_duplicates(["date", "home", "away"])
T = T.drop(columns=["open_spread", "open_total"]).merge(dk, on=["date", "home", "away"], how="left")
INJ_COLS = [c for c in T.columns if any(k in c for k in ("miss_off", "miss_def", "n_out"))]
TN = T.drop(columns=INJ_COLS)

def walk(TT, suffix):
    rows = []
    for test in (2024, 2025, 2026):
        train = list(range(2022, test))
        with contextlib.redirect_stdout(io.StringIO()):
            _, P = ns["run"](TT[TT.season.isin(train + [test])], train, test, today_suffix=suffix)
        rows.append(P.assign(season=test)[["season", "date", "home", "away", "pred_margin"]])
    return pd.concat(rows, ignore_index=True)
A = walk(T, "_open").rename(columns={"pred_margin": "m_inj"})
B = walk(TN, None).rename(columns={"pred_margin": "m_noinj"})
for X in (A, B): X["date"] = pd.to_datetime(X.date).dt.strftime("%Y-%m-%d")
G = A.merge(B, on=["season", "date", "home", "away"]).merge(T[["date", "home", "away", "home_pts", "away_pts", "open_spread"]], on=["date", "home", "away"])
G = G.dropna(subset=["open_spread", "home_pts"])
# games played before the date (both teams 10+)
L = pd.concat([T[["season", "date", "home"]].rename(columns={"home": "team"}), T[["season", "date", "away"]].rename(columns={"away": "team"})]).sort_values("date")
L["n"] = L.groupby(["season", "team"]).cumcount()
nmap = L.set_index(["date", "team"]).n
G["hn"] = nmap.reindex(pd.MultiIndex.from_arrays([G.date, G.home])).values; G["an"] = nmap.reindex(pd.MultiIndex.from_arrays([G.date, G.away])).values
G = G[(G.hn >= 10) & (G.an >= 10)].copy()
G["mg"] = G.home_pts - G.away_pts
G["early"] = pd.to_datetime(G.date).dt.month.isin([10, 11, 12, 1])

out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
def bets(m):
    e = G[m] + G.open_spread; k = e.abs() >= 3
    X = G[k].copy(); X["e"] = e[k]; X["side"] = np.sign(X.e)
    r = X.side * (X.mg + X.open_spread); X["units"] = np.where(r > 0, 100 / 110, np.where(r < 0, -1.0, 0.0)); X["res"] = r
    X["home_dog"] = (X.side > 0) & (X.open_spread > 0)
    return X
BA, BB = bets("m_inj"), bets("m_noinj")
say("NBA spreads, Model 1 walk-forward (lag 1), DK openers 2023-24..2025-26, edge 3+, both teams 10+ games, -110")
say(f"games: {len(G)}; injury shift (with minus without) mean {(G.m_inj - G.m_noinj).mean():+.2f}, sd {(G.m_inj - G.m_noinj).std():.2f}")
def row(X, lab):
    w, l = int((X.res > 0).sum()), int((X.res < 0).sum())
    by = " ".join(f"{s}:{X[X.season == s].units.sum():+.1f}" for s in (2024, 2025, 2026))
    say(f"  {lab:50s} {w + l:4d} bets {w / max(w + l, 1):6.1%} {X.units.sum():+7.1f}u ({X.units.mean() * 100 if len(X) else 0:+5.1f}/100)  [{by}]")
for lab, X in (("(a) WITH injuries", BA), ("(b) WITHOUT injuries", BB)):
    say(f"\n{lab}")
    row(X, "all bets"); row(X[X.home_dog], "home underdogs"); row(X[~X.home_dog], "everything else")
    row(X[X.home_dog & X.early], "home underdogs, Oct-Jan"); row(X[~X.home_dog & X.early], "everything else, Oct-Jan")
key = ["date", "home", "away"]
ha = BA[BA.home_dog].set_index(key); hb = BB[BB.home_dog].set_index(key)
made = ha[~ha.index.isin(hb.index)].reset_index(); shared = ha[ha.index.isin(hb.index)].reset_index(); dropped = hb[~hb.index.isin(ha.index)].reset_index()
say("\nHome-dog bets by model")
row(shared, "in both (a) and (b)"); row(made, "injury-made: only with injuries (a)"); row(dropped, "only without injuries (b)")
x = BA[BA.home_dog]
say(f"  (a) home-dog bets: injury shift toward home, mean {(x.m_inj - x.m_noinj).mean():+.2f} pts")

rng = np.random.default_rng(SEED)
def boot(X):
    parts = [X[X.season == s].units.values for s in (2024, 2025, 2026)]
    return np.array([np.concatenate([rng.choice(p, len(p)) for p in parts if len(p)]).mean() for _ in range(BOOT)])
ua, ub = BA[BA.home_dog].units.mean(), BB[BB.home_dog].units.mean()
d = boot(BB[BB.home_dog]) - boot(BA[BA.home_dog])
say("\nPRIMARY TEST: ROI per bet of home-dog bets, (b) without injuries minus (a) with")
say(f"  (a) {ua * 100:+.1f}/100, (b) {ub * 100:+.1f}/100, difference {(ub - ua) * 100:+.1f}/100; bootstrap 10th percentile "
    f"{np.percentile(d, 10) * 100:+.1f}, 90% range {np.percentile(d, 5) * 100:+.1f} to {np.percentile(d, 95) * 100:+.1f}; "
    f"injury-made home-dog ROI {made.units.mean() * 100 if len(made) else float('nan'):+.1f}/100")
diff = ub - ua
v = "REJECTED" if diff <= 0 else ("CONFIRMED" if diff >= 0.05 and np.percentile(d, 10) > 0 and len(made) and made.units.mean() < 0 else "INCONCLUSIVE")
say(f"  VERDICT (pre-registered rule): {v}")
pd.concat([BA.assign(model="with_injuries"), BB.assign(model="without_injuries")]).to_csv(
    os.path.join(W, "analysis", "homedog_injury_ablation_bets.csv"), index=False)
open(os.path.join(W, "analysis", "homedog_injury_ablation_output.txt"), "w").write("\n".join(out) + "\n")
