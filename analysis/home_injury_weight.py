"""NBA spreads: separate weight for injury shifts toward the home team, Oct-Jan (Nov 6, 2026).

Pre-registered: betting-goals/models/tests/NBA_HOME_INJURY_WEIGHT_PREREG.md (pushed 87185c3 before fitting).
m_inj / m_no: Model 1 walk-forward with / without injury features (same as analysis/homedog_injury_ablation.py), 2023-24..2025-26.
s = m_inj - m_no; m_w = m_no + w_pos*max(s,0) + w_neg*min(s,0), weights fit leave-one-season-out on Oct-Jan games (both teams 10+).
  python analysis/home_injury_weight.py .  -> analysis/home_injury_weight_output.txt, analysis/home_injury_weight_bets.csv"""
import os, sys, io, contextlib
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
sys.path.insert(0, W); os.chdir(W)
BOOT, SEED, SEAS = 10000, 20261106, (2024, 2025, 2026)
T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"))
dk = O[O.book == "draftkings"][["date", "home", "away", "open_spread", "close_spread", "open_total"]].drop_duplicates(["date", "home", "away"])
T = T.drop(columns=["open_spread", "open_total"]).merge(dk, on=["date", "home", "away"], how="left")

cache = os.path.join(W, "_tmp", "nba_m1_inj_noinj.csv")
if not os.path.exists(cache):
    src = open(os.path.join(W, "nba_mixed_model.py")).read()
    ns = {"__name__": "nm_lag"}
    exec(compile(src.replace("past = L_all[L_all.date < d]", "past = L_all[L_all.date < d - pd.Timedelta(days=LAG_DAYS)]"), "nm_lag", "exec"), ns)
    ns["LAG_DAYS"] = 1
    TN = T.drop(columns=[c for c in T.columns if any(k in c for k in ("miss_off", "miss_def", "n_out"))])
    def walk(TT, suffix, col):
        rows = []
        for test in SEAS:
            with contextlib.redirect_stdout(io.StringIO()):
                _, P = ns["run"](TT[TT.season.isin(list(range(2022, test)) + [test])], list(range(2022, test)), test, today_suffix=suffix)
            rows.append(P.assign(season=test)[["season", "date", "home", "away", "pred_margin"]].rename(columns={"pred_margin": col}))
        return pd.concat(rows, ignore_index=True)
    M = walk(T, "_open", "m_inj").merge(walk(TN, None, "m_no"), on=["season", "date", "home", "away"])
    M["date"] = pd.to_datetime(M.date).dt.strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(cache), exist_ok=True); M.to_csv(cache, index=False)
M = pd.read_csv(cache)
G = M.merge(T[["date", "home", "away", "home_pts", "away_pts", "open_spread", "close_spread"]], on=["date", "home", "away"]).dropna(subset=["open_spread", "home_pts"])
L = pd.concat([T[["season", "date", "home"]].rename(columns={"home": "team"}), T[["season", "date", "away"]].rename(columns={"away": "team"})]).sort_values("date")
L["n"] = L.groupby(["season", "team"]).cumcount(); nmap = L.set_index(["date", "team"]).n
G["hn"] = nmap.reindex(pd.MultiIndex.from_arrays([G.date, G.home])).values; G["an"] = nmap.reindex(pd.MultiIndex.from_arrays([G.date, G.away])).values
G = G[(G.hn >= 10) & (G.an >= 10) & pd.to_datetime(G.date).dt.month.isin([10, 11, 12, 1])].copy()
G["mg"] = G.home_pts - G.away_pts; G["s"] = G.m_inj - G.m_no
G["sp"], G["sn"] = G.s.clip(lower=0), G.s.clip(upper=0)

out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
say("NBA spreads Oct-Jan, Model 1 walk-forward (lag 1), DK openers 2023-24..2025-26, both teams 10+ games; LOSO home-side injury weight")
say(f"games: {len(G)}; injury shift s: mean {G.s.mean():+.2f}, sd {G.s.std():.2f}, share > 0 {(G.s > 0).mean():.0%}")
G["m_w"] = np.nan
for s in SEAS:
    tr = G[G.season != s]; y = tr.mg - tr.m_no; X = tr[["sp", "sn"]].values
    w = np.clip(np.linalg.lstsq(X, y.values, rcond=None)[0], 0, 2)
    k = G.season == s
    G.loc[k, "m_w"] = G.m_no[k] + w[0] * G.sp[k] + w[1] * G.sn[k]
    say(f"  held-out {s}: w_pos (toward home) {w[0]:.2f}, w_neg (toward away) {w[1]:.2f}  (current model = 1.00, 1.00)")

say("\nScoreboard (Oct-Jan games): RMSE vs the result and beat-the-close slope (result - close on model - close)")
def slope(m):
    x = (m + G.close_spread).values; y = (G.mg + G.close_spread).values; ok = ~np.isnan(x) & ~np.isnan(y); x, y = x[ok], y[ok]
    b = (x @ y) / (x @ x); r = y - b * x; se = np.sqrt(r @ r / (len(x) - 1) / (x @ x)); return b, b / se
for lab, m in (("m_no (no injuries)", G.m_no), ("m_inj (current)", G.m_inj), ("m_w (LOSO weights)", G.m_w), ("DK opener", -G.open_spread), ("DK close", -G.close_spread)):
    rm = np.sqrt(((G.mg - m) ** 2).mean())
    sl = slope(m) if "DK" not in lab else (np.nan, np.nan)
    say(f"  {lab:22s} RMSE {rm:.3f}" + (f" | slope vs close {sl[0]:+.3f} (t {sl[1]:+.1f})" if not np.isnan(sl[0]) else ""))

def bets(col):
    e = G[col] + G.open_spread; X = G[e.abs() >= 3].copy(); X["e"] = e[e.abs() >= 3]; X["side"] = np.sign(X.e)
    r = X.side * (X.mg + X.open_spread); X["res"] = r; X["units"] = np.where(r > 0, 100 / 110, np.where(r < 0, -1.0, 0.0))
    X["home_dog"] = (X.side > 0) & (X.open_spread > 0); X["model"] = col; return X
def row(X, lab):
    w, l = int((X.res > 0).sum()), int((X.res < 0).sum())
    by = " ".join(f"{s}:{X[X.season == s].units.sum():+.1f}" for s in SEAS)
    say(f"  {lab:44s} {w + l:4d} bets {w / max(w + l, 1):6.1%} {X.units.sum():+7.1f}u ({X.units.mean() * 100 if len(X) else 0:+5.1f}/100)  [{by}]")
B = {c: bets(c) for c in ("m_inj", "m_w", "m_no")}
for c, lab in (("m_inj", "current (with injuries)"), ("m_w", "home-side weight (LOSO)"), ("m_no", "no injuries")):
    say(f"\n{lab}")
    row(B[c][B[c].home_dog], "home underdogs"); row(B[c][~B[c].home_dog], "live-filter bets (no home dogs)")

rng = np.random.default_rng(SEED)
def boot(X):
    parts = [X[X.season == s].units.values for s in SEAS]
    return np.array([np.concatenate([rng.choice(p, len(p)) for p in parts if len(p)]).mean() for _ in range(BOOT)])
hw, hi = B["m_w"][B["m_w"].home_dog], B["m_inj"][B["m_inj"].home_dog]
d = boot(hw) - boot(hi); diff = hw.units.mean() - hi.units.mean()
lw, li = B["m_w"][~B["m_w"].home_dog].units.mean(), B["m_inj"][~B["m_inj"].home_dog].units.mean()
say("\nPRIMARY TEST: Oct-Jan home-dog ROI, LOSO home-side weight minus current")
say(f"  current {hi.units.mean() * 100:+.1f}/100, weighted {hw.units.mean() * 100:+.1f}/100, difference {diff * 100:+.1f}/100; bootstrap 10th percentile "
    f"{np.percentile(d, 10) * 100:+.1f}, 90% range {np.percentile(d, 5) * 100:+.1f} to {np.percentile(d, 95) * 100:+.1f}")
say(f"  guard: live-filter bets current {li * 100:+.1f}/100, weighted {lw * 100:+.1f}/100 (change {(lw - li) * 100:+.1f})")
v = "REJECTED" if diff <= 0 else ("CONFIRMED" if diff >= 0.05 and np.percentile(d, 10) > 0 and lw >= li - 0.02 else "INCONCLUSIVE")
say(f"  VERDICT (pre-registered rule): {v}")
pd.concat(B.values()).to_csv(os.path.join(W, "analysis", "home_injury_weight_bets.csv"), index=False)
open(os.path.join(W, "analysis", "home_injury_weight_output.txt"), "w").write("\n".join(out) + "\n")
