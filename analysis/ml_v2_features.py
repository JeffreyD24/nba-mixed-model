"""NBA moneyline v2, step 2: model inputs per game, all using results through TWO nights before the game (the repo's one-day lag,
so everything is known when DraftKings posts the opener ~24 h before tip).
  M1 team ratings: decayed ridge on game margins (team random effects, exponential time decay; tau in TAUS)
  M2 availability: value of players missing from the team's latest game (on/off-style rating, consistent across all seasons)
  M3 Elo with margin of victory (FiveThirtyEight NBA settings)
python3 analysis/ml_v2_features.py  -> analysis/ml_v2_features.csv.gz"""
import os, bisect, numpy as np, pandas as pd
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); J = lambda *p: os.path.join(W, *p)
G = pd.read_csv(J("analysis", "ml_v2_games.csv.gz"), parse_dates=["date"])
LAG = pd.Timedelta(days=2)
teams = sorted(set(G.home) | set(G.away)); ix = {t: i for i, t in enumerate(teams)}; nT = len(teams)
hi, ai = G.home.map(ix).values, G.away.map(ix).values; mg = G.margin.clip(-30, 30).values.astype(float); dd = G.date.values

# ---------------- M1: decayed ridge ratings
TAUS = [30, 60, 120]; LAM = 20.0
dates = np.unique(dd); LAGN = np.timedelta64(2, "D")
for tau in TAUS:
    rd = np.full(len(G), np.nan); hca_out = np.full(len(G), np.nan)
    for d in dates:
        cut = d - LAGN; use = (dd <= cut) & (dd > cut - np.timedelta64(400, "D"))
        if use.sum() < 100: continue
        age = (cut - dd[use]).astype("timedelta64[D]").astype(float); w = np.exp(-age / tau)
        X = np.zeros((use.sum(), nT + 1)); r = np.arange(use.sum()); X[r, hi[use]] = 1; X[r, ai[use]] = -1; X[:, nT] = 1
        P = np.eye(nT + 1) * LAM; P[nT, nT] = 1e-6
        beta = np.linalg.solve(X.T @ (X * w[:, None]) + P, X.T @ (w * mg[use]))
        g = np.where(dd == d)[0]; rd[g] = beta[hi[g]] - beta[ai[g]]; hca_out[g] = beta[nT]
    G[f"rd_{tau}"] = rd; G[f"hca_{tau}"] = hca_out
    print("M1 tau", tau, "done; missing", np.isnan(rd).sum())

# ---------------- M3: Elo (538: K=20, home +100, MOV multiplier, 75% carry-over to 1505 between seasons)
elo = {t: 1500.0 for t in teams}; hist = {t: ([pd.Timestamp("1900-01-01")], [1500.0]) for t in teams}; last_season = None
for d, day in G.groupby("date", sort=True):
    s = day.season.iloc[0]
    if s != last_season:
        for t in teams:
            elo[t] = 0.75 * elo[t] + 0.25 * 1505; hist[t][0].append(d - pd.Timedelta(days=30)); hist[t][1].append(elo[t])
        last_season = s
    for r in day.itertuples():
        diff = elo[r.home] + 100 - elo[r.away]; e = 1 / (1 + 10 ** (-diff / 400)); res = float(r.margin > 0)
        wdiff = diff if r.margin > 0 else -diff
        k = 20 * (abs(r.margin) + 3) ** 0.8 / (7.5 + 0.006 * wdiff)
        elo[r.home] += k * (res - e); elo[r.away] -= k * (res - e)
    for t in set(day.home) | set(day.away): hist[t][0].append(d); hist[t][1].append(elo[t])
def elo_at(t, d):
    ds, vs = hist[t]; j = bisect.bisect_right(ds, d - LAG) - 1; return vs[j]
G["elo_diff"] = [elo_at(h, d) - elo_at(a, d) for h, a, d in zip(G.home, G.away, G.date)]   # (home court added by the final layer)
print("M3 done")

# ---------------- M2: availability
P = pd.read_csv(J("data", "external", "nba_box", "player_games_2012_2026.csv.gz"), dtype={"player_id": str, "game_id": str}, parse_dates=["date"])
P["plus_minus"] = pd.to_numeric(P.plus_minus, errors="coerce").fillna(0)
tm = P.groupby(["game_id", "team"]).agg(pm=("plus_minus", "sum"), m=("minutes", "sum")).reset_index()
tm["tmargin"] = tm.pm / 5
P = P.merge(tm[["game_id", "team", "tmargin"]], on=["game_id", "team"])
P["rel"] = P.plus_minus - P.minutes / 48 * P.tmargin           # on-court margin relative to the team's game margin
pl = P[P.played == 1]
prior = pl.groupby(["season", "player_id"]).agg(pm=("rel", "sum"), m=("minutes", "sum"))
prior.index = prior.index.set_levels(prior.index.levels[0] + 1, level=0)   # last season's totals, keyed by this season
prior = prior.to_dict("index")
K = 1000.0
out = []
for (season, team), gm in P.groupby(["season", "team"], sort=False):
    gm = gm.sort_values("date"); games = gm.groupby(["date", "game_id"], sort=True)
    played_in = {}; cum = {}       # player -> (rel, minutes, games played for this team this season)
    seq = []                        # (date, set of players who played, snapshot of cum)
    for (d, gid), g in games:
        on = set(g[g.played == 1].player_id)
        for r in g[g.played == 1].itertuples():
            c = cum.get(r.player_id, (0.0, 0.0, 0)); cum[r.player_id] = (c[0] + r.rel, c[1] + r.minutes, c[2] + 1)
        seq.append((d, on, dict(cum), len(seq) + 1))
    out.append(pd.DataFrame(dict(season=season, team=team, ref_date=[s[0] for s in seq], seq=seq)))
REF = pd.concat(out, ignore_index=True)
REF = REF.sort_values(["season", "team", "ref_date"])
REFg = {k: v for k, v in REF.groupby(["season", "team"])}
def missed_fast(season, team, d):
    R = REFg.get((season, team))
    if R is None: return 0.0, 0
    j = R.ref_date.searchsorted(d - LAG, side="right") - 1
    if j < 0: return 0.0, 0
    rd, on, cum, ngames = R.iloc[j].seq
    if (d - rd).days > 10: return 0.0, 0
    v = 0.0; n = 0
    for p, (rel, mins, gp) in cum.items():
        if p in on or gp < 3 or mins / ngames < 10: continue
        pr = prior.get((season, p), {"pm": 0.0, "m": 0.0}); tot_m = pr["m"] + mins
        v += mins / ngames / 48 * ((pr["pm"] + rel) / tot_m * 48 * tot_m / (tot_m + K)); n += 1
    return v, n
for side in ("home", "away"):
    res = [missed_fast(s, t, d) for s, t, d in zip(G.season, G[side], G.date)]
    G[f"mv_{side[0]}"] = [r[0] for r in res]; G[f"nout_{side[0]}"] = [r[1] for r in res]
print("M2 done; share of team-games with a rotation player out: home %.2f" % (G.nout_h > 0).mean())
G.to_csv(J("analysis", "ml_v2_features.csv.gz"), index=False)
print(G.groupby("season")[["rd_60", "elo_diff", "mv_h", "mv_a"]].agg(["count", "std"]).round(2).to_string())
