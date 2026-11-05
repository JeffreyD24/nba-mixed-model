"""NBA 1st-quarter lines from who actually starts — as pre-registered in research/derivatives/STARTERS_1Q_PREREG_2026-11-05.md.
Player offense/defense ratings from on-court stints (ridge, refit weekly on games before that week), starters' 1Q prediction,
gap vs DraftKings' 1Q close, calibrated on 2023-24, tested on 2024-25 + 2025-26.
  python analysis/starters_1q.py WORKDIR -> analysis/starters_1q_output.txt, analysis/starters_1q_games.csv.gz"""
import os, sys
import numpy as np, pandas as pd
from scipy import sparse
from sklearn.linear_model import Ridge
W = os.path.abspath(sys.argv[1])
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
rng = np.random.default_rng(1105)
FIT, TEST = [2024], [2025, 2026]
LAMBDAS = [50, 150, 400, 1000]          # ridge penalty, in stint-minutes (weights = seconds / 60)

S = pd.read_csv(os.path.join(W, "data", "nba_stints_hist.csv.gz"), dtype={"espn_event_id": str})
S = S[S.sec > 0].copy(); S["d"] = pd.to_datetime(S.date)
S["hp"] = S.home_players.astype(str).str.split("|"); S["ap"] = S.away_players.astype(str).str.split("|")
S = S[(S.hp.str.len() == 5) & (S.ap.str.len() == 5)]
players = sorted(set(p for l in S.hp for p in l) | set(p for l in S.ap for p in l)); ix = {p: i for i, p in enumerate(players)}; NP = len(players)
say(f"stints {len(S)}, players {NP}, seasons {sorted(S.season.unique())}")

# design: 2 rows per stint (home offense, away offense); columns [O_0..O_NP, D_0..D_NP]
def design(D):
    n = len(D); rows, cols = [], []
    for k, (o, d) in enumerate((("hp", "ap"), ("ap", "hp"))):
        for j, (ol, dl) in enumerate(zip(D[o].values, D[d].values)):
            r = k * n + j
            rows += [r] * 10; cols += [ix[p] for p in ol] + [NP + ix[p] for p in dl]
    X = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(2 * n, 2 * NP))
    y = np.concatenate([D.home_pts.values / D.sec.values, D.away_pts.values / D.sec.values]) * 720
    w = np.concatenate([D.sec.values, D.sec.values]) / 60.0
    return X, y, w
X_all, y_all, w_all = design(S)
season_of = np.concatenate([S.season.values, S.season.values]); date_of = np.concatenate([S.d.values, S.d.values])

# games to predict: quarter scores + DK 1Q close + starters (box)
LS = pd.read_csv(os.path.join(W, "data", "period_history", "nba_linescores.csv"))
LS["d"] = pd.to_datetime(LS.date); LS["season"] = LS.d.dt.year + (LS.d.dt.month >= 8)
L = pd.read_csv(os.path.join(W, "data", "period_history", "nba_period_lines.csv.gz"))
def dk(per):
    return L[(L.period == per) & (L.book == "DraftKings")].drop_duplicates(["date", "home", "away"], keep="last")
q = dk("firstquarter")[["date", "home", "away", "home_spread", "home_spread_odds", "away_spread_odds", "total", "over_odds", "under_odds"]]
g = dk("game")[["date", "home", "away", "home_spread", "total"]].rename(columns={"home_spread": "fg_spread", "total": "fg_total"})
h1 = dk("firsthalf")[["date", "home", "away", "home_spread", "total"]].rename(columns={"home_spread": "h1_spread", "total": "h1_total"})
G = LS.merge(q, on=["date", "home", "away"]).merge(g, on=["date", "home", "away"], how="left").merge(h1, on=["date", "home", "away"], how="left")
G = G[G.season.isin(FIT + TEST)]
# starters from the first stint of each game (matches the box-score starter flag 500/500)
first = S[S.period == 1].sort_values("start_left", ascending=False).groupby(["date", "home", "away"]).first().reset_index()[["date", "home", "away", "hp", "ap"]]
G = G.merge(first, on=["date", "home", "away"])
say(f"games with DK 1Q close + starters: {len(G)} by season {G.season.value_counts().sort_index().to_dict()}")

# previous-game starters (surprise start)
B = pd.read_csv(os.path.join(W, "data", "external", "nba_box", "player_games_2012_2026.csv.gz"), dtype={"player_id": str, "game_id": str})
B = B[(B.season >= 2023) & (B.starter == 1)]
fives = B.groupby(["season", "date", "team"]).player_id.apply(lambda x: frozenset(x)).reset_index().sort_values("date")
fives["prev"] = fives.groupby(["season", "team"]).player_id.shift()
fives["changed"] = [np.nan if p is None or (isinstance(p, float)) else int(len(c - p)) for c, p in zip(fives.player_id, fives.prev)]
chg = fives.set_index(["date", "team"]).changed

def fit_predict(lam):
    preds = {}
    weeks = sorted(set(pd.to_datetime(G.date).dt.to_period("W-SUN").dt.start_time))
    for wk in weeks:
        tr = (date_of < np.datetime64(wk))
        sw = w_all * np.where(tr, 0.5 ** np.clip(G[pd.to_datetime(G.date).dt.to_period("W-SUN").dt.start_time == wk].season.iloc[0] - season_of, 0, None), 0)
        keep = sw > 0
        m = Ridge(alpha=lam, solver="sparse_cg", max_iter=300, tol=1e-4).fit(X_all[keep], y_all[keep], sample_weight=sw[keep])
        O = dict(zip(players, m.coef_[:NP])); Dd = dict(zip(players, m.coef_[NP:]))
        Gw = G[pd.to_datetime(G.date).dt.to_period("W-SUN").dt.start_time == wk]
        for r in Gw.itertuples():
            hp = m.intercept_ + sum(O.get(p, 0) for p in r.hp) + sum(Dd.get(p, 0) for p in r.ap)
            ap = m.intercept_ + sum(O.get(p, 0) for p in r.ap) + sum(Dd.get(p, 0) for p in r.hp)
            preds[r.Index] = (hp, ap)
    return pd.DataFrame.from_dict(preds, orient="index", columns=["p_home", "p_away"])

def score(G2):
    G2 = G2.copy()
    G2["m1q"] = G2.home_q1 - G2.away_q1; G2["t1q"] = G2.home_q1 + G2.away_q1
    G2["pm"] = G2.p_home - G2.p_away; G2["pt"] = G2.p_home + G2.p_away
    G2["y_s"] = G2.m1q + G2.home_spread; G2["gap_s"] = G2.pm + G2.home_spread      # home cover margin; starters' gap
    G2["y_t"] = G2.t1q - G2.total; G2["gap_t"] = G2.pt - G2.total
    return G2

# choose lambda on 2023-24 by 1Q squared error (margin + total) of the raw starters' prediction
say("\nlambda choice on 2023-24 (1Q squared error of starters' prediction, margin / total):")
best, cache = None, {}
for lam in LAMBDAS:
    P = fit_predict(lam); Gs = score(G.join(P, how="inner")); F = Gs[Gs.season.isin(FIT)]
    e = ((F.m1q - F.pm) ** 2).mean() + ((F.t1q - F.pt) ** 2).mean()
    say(f"  lambda {lam}: margin MSE {((F.m1q - F.pm) ** 2).mean():.2f}, total MSE {((F.t1q - F.pt) ** 2).mean():.2f}; DK line margin MSE {((F.m1q + F.home_spread) ** 2).mean():.2f}, total {((F.t1q - F.total) ** 2).mean():.2f}")
    cache[lam] = Gs
    if best is None or e < best[0]: best = (e, lam)
lam = best[1]; Gs = cache[lam]; say(f"chosen lambda {lam}")

F = Gs[Gs.season.isin(FIT)]; T = Gs[Gs.season.isin(TEST)].copy()
bs = (F["gap_s"] * F["y_s"]).sum() / (F["gap_s"] ** 2).sum(); bt = (F["gap_t"] * F["y_t"]).sum() / (F["gap_t"] ** 2).sum()
say(f"calibration (2023-24): spread b = {bs:.3f}, total b = {bt:.3f}  (gap sd {F["gap_s"].std():.2f} / {F["gap_t"].std():.2f})")
T["e_s"] = bs * T["gap_s"]; T["e_t"] = bt * T["gap_t"]

def boot(df, f, n=4000):
    dates = df.date.values; ud = np.unique(dates); grp = {d: np.where(dates == d)[0] for d in ud}
    vals = []
    for _ in range(n):
        pick = np.concatenate([grp[d] for d in rng.choice(ud, len(ud))]); vals.append(f(df.iloc[pick]))
    return np.percentile(vals, 5), np.percentile(vals, 95)
def dec(a): a = np.where(pd.isna(a), -110, a); return np.where(a > 0, a / 100, 100 / np.abs(a))

say("\n== TEST 2024-25 + 2025-26 ==")
res = {}
for lab, y, e, side_odds in (("1Q spread", "y_s", "e_s", ("home_spread_odds", "away_spread_odds")), ("1Q total", "y_t", "e_t", ("over_odds", "under_odds"))):
    gain = lambda d: (d[y] ** 2).mean() - ((d[y] - d[e]) ** 2).mean()
    lo, hi = boot(T, gain)
    Bt = T[T[e].abs() >= 1.0].copy(); s = np.sign(Bt[e]); r = s * Bt[y]
    pr = np.where(s > 0, Bt[side_odds[0]], Bt[side_odds[1]]); u = np.where(r > 0, dec(pr), np.where(r < 0, -1.0, 0.0))
    Bt["u"] = u; Bt["r"] = r
    w = (r[r != 0] > 0).mean() if len(Bt) else float("nan")
    ulo, uhi = boot(Bt, lambda d: d.u.mean(), 2000) if len(Bt) >= 5 else (float("nan"), float("nan"))
    p1 = (lo > 0); p2 = bool(len(Bt)) and (w > 0.5238) and u.sum() > 0
    res[lab] = p1 and p2
    say(f"{lab}: squared-error gain vs DK close {gain(T):+.3f} [{lo:+.3f}, {hi:+.3f}] (n {len(T)}) | bets {len(Bt)}: {w*100:.1f}%, {u.sum():+.1f}u "
        f"({u.mean()*100:+.1f}% [{ulo*100:+.1f}, {uhi*100:+.1f}]) -> {'PASS' if res[lab] else 'fail'}")
    for sname in TEST:
        b = Bt[Bt.season == sname]; t = T[T.season == sname]
        say(f"     {sname}: gain {gain(t):+.3f}, bets {len(b)}" + (f", {(b.r[b.r != 0] > 0).mean()*100:.1f}%, {b.u.sum():+.1f}u" if len(b) else ""))
    # descriptive (not the pre-registered rule): top 10% of |gap| by raw sign, to see whether any slice carries signal
    cut = T[e.replace("e_", "gap_")].abs().quantile(0.9); Z = T[T[e.replace("e_", "gap_")].abs() >= cut]
    rz = np.sign(Z[e.replace("e_", "gap_")]) * Z[y]; rz = rz[rz != 0]
    say(f"     descriptive: biggest 10% of raw gaps (|gap| >= {cut:.2f}), side = gap direction: {len(rz)} games, {(rz > 0).mean()*100:.1f}% win")
    T[f"bet_{lab[3:]}"] = T[e].abs() >= 1.0

say("\n== Accuracy (test): 1Q margin / total MSE ==")
say(f"  DK close line: {((T.m1q + T.home_spread) ** 2).mean():.2f} / {((T.t1q - T.total) ** 2).mean():.2f}")
say(f"  starters' raw prediction: {((T.m1q - T.pm) ** 2).mean():.2f} / {((T.t1q - T.pt) ** 2).mean():.2f}")
say(f"  DK close + calibrated gap: {((T["y_s"] - T["e_s"]) ** 2).mean():.2f} / {((T["y_t"] - T["e_t"]) ** 2).mean():.2f}")

say("\n== Side: surprise starts (a team's starting five differs from its last game) ==")
T["h_chg"] = [chg.get((d, h), np.nan) for d, h in zip(T.date, T.home)]; T["a_chg"] = [chg.get((d, a), np.nan) for d, a in zip(T.date, T.away)]
T["surprise"] = (T.h_chg.fillna(0) + T.a_chg.fillna(0)) > 0
for k, d in T.groupby("surprise"):
    say(f"  surprise={k}: games {len(d)}, |spread gap| {d["gap_s"].abs().mean():.2f}, spread gain {(d["y_s"] ** 2).mean() - ((d["y_s"] - d["e_s"]) ** 2).mean():+.3f}, "
        f"total gain {(d["y_t"] ** 2).mean() - ((d["y_t"] - d["e_t"]) ** 2).mean():+.3f}")
say("\n== Side: does the 1Q starters' gap also predict the 1st half / full game cover? (test, corr with cover margin) ==")
T["y_h1"] = (T.home_q1 + T.home_q2 - T.away_q1 - T.away_q2) + T.h1_spread; T["y_fg"] = (T.home_final - T.away_final) + T.fg_spread
for c in ("y_s", "y_h1", "y_fg"):
    d = T[[c, "gap_s"]].dropna(); say(f"  {c}: corr {np.corrcoef(d[c], d["gap_s"])[0,1]:+.3f} (n {len(d)})")

say("\n== Verdict ==")
for k, v in res.items(): say(f"{k}: {'PASS -> PROVISIONAL after Fable check' if v else 'did not pass'}")
T.drop(columns=["hp", "ap"]).to_csv(os.path.join(W, "analysis", "starters_1q_games.csv.gz"), index=False)
open(os.path.join(W, "analysis", "starters_1q_output.txt"), "w").write("\n".join(out) + "\n")
