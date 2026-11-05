"""Why the QB / player-based NFL model predicts spreads worse than the team model and the market. Walk-forward 2020-25 (fit on
2018+ earlier seasons), regular season, graded vs actual margins (MAE) and at DK openers (edge 3+).
  1. how stable QB efficiency is (season to season, and within a season)
  2. the "wrong QB" problem: games where the starter wasn't who started last game
  3. variants: actual starter, opponent-adjusted, CPOE, longer memory, + special teams, + points-based rating, + team model
  python analysis/nfl_qb_diagnostics.py WORKDIR NFL_REPO"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
cols = ["game_id", "season", "week", "season_type", "game_date", "home_team", "away_team", "posteam", "defteam", "play_type",
        "epa", "qb_dropback", "rush", "passer_player_id", "passer_player_name", "cpoe", "special_teams_play", "home_score", "away_score"]
P = pd.concat([pd.read_csv(f, usecols=lambda c: c in cols, low_memory=False) for f in sorted(glob.glob(os.path.join(N, "data", "external", "nflverse", "play_by_play_*_cols.csv.gz")))])
CANON = {"LA": "lar", "WAS": "wsh", "OAK": "lv", "SD": "lac", "STL": "lar"}; code = lambda t: CANON.get(t, str(t).lower())
P = P[P.posteam.notna() & P.epa.notna()].copy()
for c in ("home_team", "away_team", "posteam", "defteam"): P[c] = P[c].map(code)
P = P[P.season_type == "REG"]
sc = P[P.play_type.isin(["pass", "run"])]; st = P[P.special_teams_play == 1]
db = sc[sc.qb_dropback == 1]; ru = sc[sc.rush == 1]
G = sc.groupby(["game_id", "posteam"]).agg(season=("season", "first"), week=("week", "first"), date=("game_date", "first"),
        opp=("defteam", "first"), home=("home_team", "first"), hs=("home_score", "max"), as_=("away_score", "max"), plays=("epa", "size")).reset_index()
G = G.merge(db.groupby(["game_id", "posteam"]).epa.agg(db="size", pass_s="sum").reset_index(), on=["game_id", "posteam"], how="left")
G = G.merge(ru.groupby(["game_id", "posteam"]).epa.agg(ru="size", rush_s="sum").reset_index(), on=["game_id", "posteam"], how="left")
G = G.merge(st.groupby(["game_id", "posteam"]).epa.agg(st_s="sum").reset_index(), on=["game_id", "posteam"], how="left")
stq = db[db.passer_player_id.notna()].groupby(["game_id", "posteam", "passer_player_id"]).agg(n=("epa", "size"), s=("epa", "sum"),
        cp=("cpoe", "sum"), cpn=("cpoe", "count")).reset_index()
start = stq.sort_values("n").groupby(["game_id", "posteam"]).tail(1).rename(columns={"passer_player_id": "qb"})
G = G.merge(start[["game_id", "posteam", "qb"]], on=["game_id", "posteam"], how="left")
G["date"] = pd.to_datetime(G.date); G = G.sort_values(["date", "game_id"]).reset_index(drop=True)
G["is_home"] = (G.posteam == G.home).astype(int)
G["pts_for"] = np.where(G.is_home == 1, G.hs, G.as_); G["pts_against"] = np.where(G.is_home == 1, G.as_, G.hs)
G = G.fillna({"st_s": 0.0})
LGP = db.epa.mean(); LGR = ru.epa.mean()
stq = stq.merge(G[["game_id", "posteam", "date", "opp"]], on=["game_id", "posteam"]).sort_values("date")

# ---------- 1. stability
qs = stq.merge(G[["game_id", "posteam", "season"]], on=["game_id", "posteam"]).groupby(["passer_player_id", "season"]).agg(n=("n", "sum"), s=("s", "sum"), cp=("cp", "sum"), cpn=("cpn", "sum")).reset_index()
qs = qs[qs.n >= 250]; qs["epa"] = qs.s / qs.n; qs["cpoe"] = qs.cp / qs.cpn
nx = qs.merge(qs.assign(season=qs.season - 1), on=["passer_player_id", "season"], suffixes=("", "_next"))
ts = G.groupby(["posteam", "season"]).agg(pass_s=("pass_s", "sum"), db=("db", "sum"), rush_s=("rush_s", "sum"), ru=("ru", "sum"),
        st=("st_s", "mean"), pf=("pts_for", "mean"), pa=("pts_against", "mean")).reset_index()
ts["pe"] = ts.pass_s / ts.db; ts["re"] = ts.rush_s / ts.ru; ts["pm"] = ts.pf - ts.pa
tn = ts.merge(ts.assign(season=ts.season - 1), on=["posteam", "season"], suffixes=("", "_next"))
print("1. HOW STABLE IS EACH STAT FROM ONE SEASON TO THE NEXT (correlation; 1 = perfectly repeatable, 0 = pure noise)")
print(f"   QB EPA per dropback (same QB, 250+ dropbacks both years, {len(nx)} QB-seasons): {nx.epa.corr(nx.epa_next):.2f}")
print(f"   QB completion % over expected (CPOE), same QBs:                          {nx.cpoe.corr(nx.cpoe_next):.2f}")
print(f"   team passing EPA per dropback:                                           {tn.pe.corr(tn.pe_next):.2f}")
print(f"   team rushing EPA per carry:                                              {tn.re.corr(tn.re_next):.2f}")
print(f"   team special-teams EPA per game:                                         {tn.st.corr(tn.st_next):.2f}")
print(f"   team point margin per game:                                              {tn.pm.corr(tn.pm_next):.2f}")
# within season: first 8 games vs the rest
G["gn"] = G.groupby(["posteam", "season"]).cumcount()
a = G[G.gn < 8].groupby(["posteam", "season"]).agg(ps=("pass_s", "sum"), d=("db", "sum"), pf=("pts_for", "mean"), pa=("pts_against", "mean"))
b = G[G.gn >= 8].groupby(["posteam", "season"]).agg(ps=("pass_s", "sum"), d=("db", "sum"), pf=("pts_for", "mean"), pa=("pts_against", "mean"))
ab = a.join(b, lsuffix="1", rsuffix="2")
print(f"   within a season, games 1-8 vs 9+: team passing EPA {(ab.ps1 / ab.d1).corr(ab.ps2 / ab.d2):.2f}, point margin {(ab.pf1 - ab.pa1).corr(ab.pf2 - ab.pa2):.2f}")

# ---------- features
def ew(vals, wts, hl, prior, k):
    if len(vals) == 0: return prior
    w = 0.5 ** (np.arange(len(vals))[::-1] / hl) * wts
    return float(((w * vals).sum() + k * prior) / (w.sum() + k))
qb_hist = {q: g for q, g in stq.groupby("passer_player_id")}
by_team = {t: g for t, g in G.groupby("posteam")}; by_opp = {t: g for t, g in G.groupby("opp")}
def qb_rating(q, d, hl=16, k=250, adj=False, cp=False):
    h = qb_hist.get(q)
    if h is None: return (LGP, 0.0)
    h = h[h.date < d]
    if not len(h): return (LGP, 0.0)
    w = 0.5 ** (np.arange(len(h))[::-1] / hl)
    if adj:      # opponent-adjusted: subtract what each opponent's defense allowed per dropback that season to date (approx: full prior-season avg)
        s = h.s.values - h.n.values * h.opp_allow.values
        val = ((w * s).sum() + k * 0.0) / ((w * h.n.values).sum() + k) + LGP
    else:
        val = ((w * h.s.values).sum() + k * LGP) / ((w * h.n.values).sum() + k)
    c = ((w * h.cp.values).sum()) / ((w * h.cpn.values).sum() + 150) if cp else 0.0
    return (val, c)
# opponent pass defense allowed (expanding mean of earlier games, by defense)
G = G.sort_values("date"); G["allow_pg"] = G.pass_s / G.db
G["opp_allow"] = G.groupby("opp").apply(lambda g: (g.pass_s.cumsum().shift() / g.db.cumsum().shift())).reset_index(level=0, drop=True).fillna(LGP) - LGP
stq = stq.merge(G[["game_id", "posteam", "opp_allow"]], on=["game_id", "posteam"], how="left").fillna({"opp_allow": 0.0})
qb_hist = {q: g for q, g in stq.groupby("passer_player_id")}
rows = []
for r in G.itertuples():
    if r.season < 2018: continue
    prev = by_team[r.posteam]; prev = prev[prev.date < r.date]; prevd = by_opp[r.posteam]; prevd = prevd[prevd.date < r.date]
    if not len(prev): continue
    eq = prev.qb.iloc[-1]
    f = dict(game_id=r.game_id, team=r.posteam, season=r.season, week=r.week, is_home=r.is_home, qb_wrong=int(eq != r.qb))
    f["qb"], f["cp"] = qb_rating(eq, r.date, cp=True); f["qb_act"], _ = qb_rating(r.qb, r.date)
    f["qb_long"], _ = qb_rating(eq, r.date, hl=48, k=500); f["qb_adj"], _ = qb_rating(eq, r.date, adj=True)
    one = np.ones(len(prev))
    f["pass_team"] = ew(prev.pass_s.values / prev.db.values, prev.db.values, 8, LGP, 100)
    f["rush"] = ew(prev.rush_s.values / prev.ru.values, prev.ru.values, 8, LGR, 60)
    f["pdef"] = ew(prevd.pass_s.values / prevd.db.values, prevd.db.values, 8, LGP, 100) if len(prevd) else LGP
    f["rdef"] = ew(prevd.rush_s.values / prevd.ru.values, prevd.ru.values, 8, LGR, 60) if len(prevd) else LGR
    f["st"] = ew(prev.st_s.values, one, 8, 0.0, 4)
    f["pts"] = ew((prev.pts_for - prev.pts_against).values, one, 8, 0.0, 4)
    rows.append(f)
F = pd.DataFrame(rows)
H = F[F.is_home == 1].drop(columns="is_home").add_prefix("h_").rename(columns={"h_game_id": "game_id"})
A = F[F.is_home == 0].drop(columns="is_home").add_prefix("a_").rename(columns={"a_game_id": "game_id"})
X = H.merge(A, on="game_id"); X = X.merge(G[G.is_home == 1][["game_id", "date", "posteam", "opp", "pts_for", "pts_against"]], on="game_id")
X = X.rename(columns={"posteam": "home", "opp": "away", "h_season": "season", "h_week": "week"}); X["margin"] = X.pts_for - X.pts_against
X["date"] = X.date.dt.strftime("%Y-%m-%d")
for v in ("qb", "qb_act", "qb_long", "qb_adj"):
    X[f"pe_{v}"] = (X[f"h_{v}"] + X.a_pdef) - (X[f"a_{v}"] + X.h_pdef)     # defense = EPA allowed (higher = worse)
X["pe_team"] = (X.h_pass_team + X.a_pdef) - (X.a_pass_team + X.h_pdef)
X["re"] = (X.h_rush + X.a_rdef) - (X.a_rush + X.h_rdef); X["cpd"] = X.h_cp - X.a_cp
X["std"] = X.h_st - X.a_st; X["ptsd"] = X.h_pts - X.a_pts; X["one"] = 1.0
# market and team model
src = open(os.path.join(W, "analysis", "nfl_autopsy.py")).read().split("def u(s)")[0].split("W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])", 1)[1]
exec(src)
P = P.drop_duplicates(["date", "home", "away"])
X = X.merge(P[["date", "home", "away", "o_sp", "pm"]], on=["date", "home", "away"], how="left")
print(f"\n2. THE WRONG-QB PROBLEM: the model assumes last game's starter. Wrong in {(X.h_qb_wrong.sum() + X.a_qb_wrong.sum()) / (2 * len(X)):.1%} of team-games "
      f"({int(X.h_qb_wrong.sum() + X.a_qb_wrong.sum())} of {2 * len(X)}).")
def wf(feats, extra=None):
    out = pd.Series(np.nan, index=X.index)
    for s in range(2020, 2026):
        tr = (X.season < s) & (X.season >= 2018) & X.margin.notna(); te = X.season == s
        base_tr = X.loc[tr, extra].values if extra else 0; base_te = X.loc[te, extra].values if extra else 0
        tr2 = tr & (X[extra].notna() if extra else True)
        b = np.linalg.lstsq(X.loc[tr2, feats].values, (X.margin - (X[extra] if extra else 0))[tr2].values, rcond=None)[0]
        out[te] = X.loc[te, feats].values @ b + (X.loc[te, extra].values if extra else 0)
    return out
def report(lab, pred, mask=None):
    m = X.season.between(2020, 2025) & X.o_sp.notna() & X.pm.notna() & pred.notna()
    if mask is not None: m &= mask
    y = X.margin[m]; p = pred[m]; o = -X.o_sp[m]
    e = p - o; b = e.abs() >= 3; r = np.sign(e[b]) * (y[b] - o[b]); w, l = (r > 0).sum(), (r < 0).sum()
    print(f"  {lab:52s} MAE {np.abs(p - y).mean():6.3f}  (opener {np.abs(o - y).mean():.3f}) | {w + l:4d} bets {w / max(w + l, 1):.1%} {w * 100 / 110 - l:+6.1f}u")
print("\n3. VARIANTS (MAE vs actual margin; spread bets at the DK opener, edge 3+)")
report("team model (current live model)", X.pm)
report("player model: last game's QB (what we tested)", wf(["one", "pe_qb", "re"]))
report("  ... actual starter instead (known by kickoff)", wf(["one", "pe_qb_act", "re"]))
report("  ... QB memory 3x longer, stronger shrink", wf(["one", "pe_qb_long", "re"]))
report("  ... opponent-adjusted QB EPA", wf(["one", "pe_qb_adj", "re"]))
report("  ... + completion % over expected", wf(["one", "pe_qb", "re", "cpd"]))
report("  ... team passing instead of QB", wf(["one", "pe_team", "re"]))
report("  ... + special teams", wf(["one", "pe_qb", "re", "std"]))
report("  ... + recent point margin (scoreboard rating)", wf(["one", "pe_qb", "re", "std", "ptsd"]))
report("recent point margin alone", wf(["one", "ptsd"]))
report("team model + QB/player adjustments (fit on its misses)", wf(["one", "pe_qb", "re", "std", "ptsd"], extra="pm"))
print("\n  where the QB guess was wrong for either team:")
wrong = (X.h_qb_wrong + X.a_qb_wrong) > 0
report("  team model", X.pm, wrong); report("  player model, last game's QB", wf(["one", "pe_qb", "re"]), wrong)
report("  player model, actual starter", wf(["one", "pe_qb_act", "re"]), wrong)
print("  where it was right:")
report("  team model", X.pm, ~wrong); report("  player model", wf(["one", "pe_qb", "re"]), ~wrong)
s = 2025; tr = (X.season < s) & (X.season >= 2018)
b = np.linalg.lstsq(X.loc[tr, ["one", "pe_qb", "re", "std", "ptsd"]].values, X.margin[tr].values, rcond=None)[0]
sd = X.loc[tr, ["pe_qb", "re", "std", "ptsd"]].std().values
print("\n  points of margin per 1 standard deviation of each input (2018-24 fit):", dict(zip(["QB passing", "rushing", "special teams", "point margin"], (b[1:] * sd).round(2))))
X.to_csv(os.path.join(W, "analysis", "nfl_qb_diag.csv"), index=False)
