"""Step 1 of the NFL timing test (pre-registration: nfl-mixed-model backtests/TIMING_PREREG.md, commit 9078e64).
Team-model early totals for 2020-25 as known at three moments: T1 first DraftKings total snapshot, T2 Monday 9 AM before week k,
T3 Tuesday 11:45 AM (after week k-1's last game). Same training seasons and tuning as backtest.py; only the test-season walk-forward
changes: team effects re-solved with games on dates before the cutoff date. Also "T0" = the cutoff the existing backtest uses
(the game's own date), as a check that this reproduces backtests/predictions_*.csv.
  python analysis/nfl_timing_team.py WORKDIR NFL_REPO  -> analysis/nfl_timing_team_preds.csv, analysis/nfl_timing_cutoffs.csv"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
sys.path.insert(0, N)
import nfl_mixed_model as nm

ET = "America/New_York"
# ---------------------------------------------------------------- cutoffs per game
V = pd.read_csv(os.path.join(N, "data", "nflverse_games.csv"))
V = V[(V.game_type == "REG") & V.season.between(2020, 2025)].copy()
V["kick"] = pd.to_datetime(V.gameday + " " + V.gametime.fillna("13:00")).dt.tz_localize(ET, ambiguous="NaT", nonexistent="shift_forward")
V["gd"] = pd.to_datetime(V.gameday)
last = V.groupby(["season", "week"]).gd.max().rename("wk_last").reset_index()
last["week"] = last.week + 1                                   # week k-1's last game, keyed to week k
V = V.merge(last, on=["season", "week"], how="left")
day = pd.Timedelta(days=1)
V["T2"] = np.where(V.wk_last.dt.dayofweek == 0, V.wk_last, V.wk_last + day)
V["T2"] = (pd.to_datetime(V["T2"]) + pd.Timedelta(hours=9)).dt.tz_localize(ET)
V["T3"] = (V.wk_last + day + pd.Timedelta(hours=11, minutes=45)).dt.tz_localize(ET)

NAME = {"Arizona Cardinals": "ari", "Atlanta Falcons": "atl", "Baltimore Ravens": "bal", "Buffalo Bills": "buf", "Carolina Panthers": "car",
        "Chicago Bears": "chi", "Cincinnati Bengals": "cin", "Cleveland Browns": "cle", "Dallas Cowboys": "dal", "Denver Broncos": "den",
        "Detroit Lions": "det", "Green Bay Packers": "gb", "Houston Texans": "hou", "Indianapolis Colts": "ind", "Jacksonville Jaguars": "jax",
        "Kansas City Chiefs": "kc", "Los Angeles Chargers": "lac", "Los Angeles Rams": "lar", "Las Vegas Raiders": "lv", "Oakland Raiders": "lv",
        "Miami Dolphins": "mia", "Minnesota Vikings": "min", "New England Patriots": "ne", "New Orleans Saints": "no", "New York Giants": "nyg",
        "New York Jets": "nyj", "Philadelphia Eagles": "phi", "Pittsburgh Steelers": "pit", "Seattle Seahawks": "sea", "San Francisco 49ers": "sf",
        "Tampa Bay Buccaneers": "tb", "Tennessee Titans": "ten", "Washington Commanders": "wsh", "Washington Football Team": "wsh",
        "Washington Redskins": "wsh"}
snaps = []
for f in sorted(glob.glob(os.path.join(W, "data", "odds_history", "nfl", "*.csv.gz"))):
    d = pd.read_csv(f); d = d[(d.book == "draftkings") & (d.market == "totals") & (d.outcome == "Over")]
    if len(d): snaps.append(d[["snapshot_utc", "commence_et", "home", "away", "point"]])
S = pd.concat(snaps); S["t"] = pd.to_datetime(S.snapshot_utc, utc=True).dt.tz_convert(ET)
S["tip"] = pd.to_datetime(S.commence_et).dt.tz_localize(ET, ambiguous="NaT", nonexistent="shift_forward")
S = S[S.t < S.tip].copy(); S["h"] = S.home.map(NAME); S["a"] = S.away.map(NAME)
S["date"] = S.tip.dt.strftime("%Y-%m-%d")
unk = S[S.h.isna() | S.a.isna()][["home", "away"]].drop_duplicates()
if len(unk): print("unmapped team names:", unk.values.tolist()[:10])
code = {"LA": "lar", "LV": "lv", "OAK": "lv", "WAS": "wsh"}
V["h"] = V.home_team.map(lambda t: code.get(t, t.lower())); V["a"] = V.away_team.map(lambda t: code.get(t, t.lower()))
first = S.groupby(["date", "h", "a"]).t.min().rename("T1").reset_index()
V = V.merge(first, left_on=["gameday", "h", "a"], right_on=["date", "h", "a"], how="left").drop(columns="date")
S[["t", "date", "h", "a", "point"]].to_csv(os.path.join(W, "analysis", "nfl_timing_dk_snaps.csv.gz"), index=False)
V[["game_id", "season", "week", "gameday", "h", "a", "kick", "T1", "T2", "T3"]].to_csv(os.path.join(W, "analysis", "nfl_timing_cutoffs.csv"), index=False)
print("cutoffs: games", len(V), "| with T1", V.T1.notna().sum(), "| median days before kickoff: T1",
      round(((V.kick - V.T1).dt.total_seconds() / 86400).median(), 1), "T2", round(((V.kick - V.T2).dt.total_seconds() / 86400).median(), 1),
      "T3", round(((V.kick - V.T3).dt.total_seconds() / 86400).median(), 1), flush=True)
print("T1 after T2 (opener first seen late):", int((V.T1 > V.T2).sum()), "games", flush=True)

# ---------------------------------------------------------------- walk-forward with per-game cutoff dates
orig_wf = nm.walk_forward
def wf_cut(G, prev_O, prev_D, fit, rho_O, rho_D, half_life, adapt_n0=None, alt_suffix=None):
    if "cut" not in G or G["cut"].isna().any():
        return orig_wf(G.drop(columns="cut", errors="ignore"), prev_O, prev_D, fit, rho_O, rho_D, half_life, adapt_n0, alt_suffix)
    G = G.sort_values("date").reset_index(drop=True)
    teams = sorted(set(G.home) | set(G.away)); t_idx = {t: i for i, t in enumerate(teams)}; q = len(teams)
    prior = np.r_[[rho_O * prev_O.get(t, 0.0) for t in teams], [rho_D * prev_D.get(t, 0.0) for t in teams]]
    b = fit["b"]
    L_all = nm.long_rows(G); L_all = L_all.assign(pts=L_all.pts.astype(float))
    G2 = G.copy()
    for s in ("home", "away"):
        for c in nm.INJ: G2[f"{s}_{c}"] = G2[f"{s}_{c}{alt_suffix}"]
    L_alt = nm.long_rows(G2)
    preds = []
    for c in sorted(G.cut.unique()):
        past = L_all[(L_all.date < c) & L_all.pts.notna()]
        if len(past):
            Z = np.zeros((len(past), 2 * q)); r = np.arange(len(past))
            Z[r, past.off.map(t_idx).values] = 1; Z[r, q + past["def"].map(t_idx).values] = 1
            age = (c - past.date).dt.days.values
            w = 0.5 ** (age / half_life) if half_life else None
            _, u = nm.solve_mme(nm.xmat(past), Z, past.pts.values, fit["a_off"], fit["a_def"], w=w, z_prior=prior, fixed=b)
        else:
            u = prior
        O, D = u[:q], u[q:]
        gi_set = set(G.index[G.cut == c])
        ta = L_alt[L_alt.gid.isin(gi_set)]
        pts_alt = {(gid, ih): v for gid, ih, v in zip(ta.gid, ta.is_home, nm.xmat(ta) @ b)}
        for gi in sorted(gi_set):
            g = G.loc[gi]; h, a = t_idx[g.home], t_idx[g.away]
            eh = pts_alt[(gi, 1)] + O[h] + D[a]; ea = pts_alt[(gi, 0)] + O[a] + D[h]
            preds.append([gi, eh - ea, eh + ea])
    P = pd.DataFrame(preds, columns=["i", "tm_margin", "tm_total"]).set_index("i")
    P["pred_margin"], P["pred_total"] = P.tm_margin, P.tm_total                     # so run()'s evaluate() works
    P[f"pred_margin{alt_suffix}"], P[f"pred_total{alt_suffix}"] = P.tm_margin, P.tm_total
    return G.join(P)
nm.walk_forward = wf_cut

# ---------------------------------------------------------------- run per season and timing
df = pd.read_csv(os.path.join(N, "data", "training_games.csv")); df["date"] = pd.to_datetime(df.date)
df = df.merge(V[["game_id", "T1", "T2", "T3"]], on="game_id", how="left")
# T1 injuries: each team's previous game's early snapshot (week k-2's final report)
EC = [f"{c}_early" for c in ("qb_miss", "qbq_miss", "miss_off", "miss_def", "n_out", "report_filed")]
long = pd.concat([df[["game_id", "season", "date", "home"] + [f"home_{c}" for c in EC]].rename(columns={"home": "team", **{f"home_{c}": c for c in EC}}),
                  df[["game_id", "season", "date", "away"] + [f"away_{c}" for c in EC]].rename(columns={"away": "team", **{f"away_{c}": c for c in EC}})])
long = long.sort_values("date"); prevs = long.groupby(["season", "team"])[EC].shift(1)
long = pd.concat([long[["game_id", "team"]], prevs.add_suffix("_prev")], axis=1)
for s in ("home", "away"):
    m = df[["game_id", s]].merge(long, left_on=["game_id", s], right_on=["game_id", "team"], how="left")
    for c in EC: df[f"{s}_{c}_t1"] = m[f"{c}_prev"].values
out = []
for test in range(2020, 2026):
    train = list(range(test - 5, test))
    for T in ("T0", "T1", "T2", "T3"):
        d = df.copy()
        te = d.season == test
        if T == "T0": d.loc[te, "cut"] = d.loc[te, "date"]
        else: d.loc[te, "cut"] = pd.to_datetime(d.loc[te, T].astype(str).str[:10], errors="coerce")
        if T == "T1":   # the early snapshot (columns *_early, used for prediction) becomes the team's previous game's early snapshot
            for s in ("home", "away"):
                for c in EC: d.loc[te, f"{s}_{c}"] = d.loc[te, f"{s}_{c}_t1"].fillna(0)
        d = d[~te | d.cut.notna()]
        d = d.drop(columns=[c for c in d.columns if c.endswith("_t1")] + ["T1", "T2", "T3"])
        tst = d[d.season == test].copy(); oth = d[d.season != test].drop(columns="cut")
        # run() splits train/test itself; give the test season its cut column by passing the combined frame
        d2 = pd.concat([oth, tst])
        summ, Pt = nm.run(d2, train, test)
        out.append(Pt.assign(T=T)[["game_id", "season", "week", "T", "tm_margin", "tm_total"]])
        print(test, T, "games", len(Pt), "halflife", summ["chosen_halflife"], flush=True)
R = pd.concat(out); R.to_csv(os.path.join(W, "analysis", "nfl_timing_team_preds.csv"), index=False)
# reproduction check: T0 vs the repo's backtest predictions (early total)
B = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(N, "backtests", "predictions_20*.csv"))])
c = R[R["T"] == "T0"].merge(B[["game_id", "pred_total_early"]], on="game_id")
print("T0 vs backtest pred_total_early: n", len(c), "max abs diff", round((c.tm_total - c.pred_total_early).abs().max(), 4), flush=True)
