"""NBA player props v2 (injury/rest-aware minutes) — as pre-registered in research/props/PROPS_V2_PREREG_2026-11-05.md.
Needs _tmp/props_features.csv.gz (analysis/props_v1.py features), research/injury_history/, data/props_history/bettingpros/
(fit 2023-24, test A 2024-25) and data/props_history/nba/ (test B 2025-26, 11 AM).
  python analysis/props_v2.py WORKDIR -> analysis/props_v2_output.txt, analysis/props_v2_bets.csv.gz"""
import os, sys, re, glob, json
import numpy as np, pandas as pd
from scipy import stats, optimize
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, os.path.join(W, "analysis")); sys.path.insert(0, W)
import derived  # RULE 4: saved features in derived/ (restored to _tmp/props_features.csv if _tmp lacks the .gz)
FEAT = os.path.join(W, "_tmp", "props_features.csv.gz")
if not os.path.exists(FEAT): derived.ensure(W, ["props_features.csv"]); FEAT = os.path.join(W, "_tmp", "props_features.csv")
from props_unders import load_bp, norm, dec
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
rng = np.random.default_rng(1106)
P1 = json.load(open(os.path.join(W, "data", "props_v1b_params.json")))
STATS = ["pts", "reb", "ast", "fg3m"]; PACE = {"pts": True, "ast": True, "fg3m": True, "reb": False}
FIT, TEST_A = 2024, 2025
FULL = {"Atlanta Hawks": "atl", "Boston Celtics": "bos", "Brooklyn Nets": "bkn", "Charlotte Hornets": "cha", "Chicago Bulls": "chi",
        "Cleveland Cavaliers": "cle", "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Detroit Pistons": "det", "Golden State Warriors": "gs",
        "Houston Rockets": "hou", "Indiana Pacers": "ind", "LA Clippers": "lac", "Los Angeles Clippers": "lac", "Los Angeles Lakers": "lal",
        "Memphis Grizzlies": "mem", "Miami Heat": "mia", "Milwaukee Bucks": "mil", "Minnesota Timberwolves": "min", "New Orleans Pelicans": "no",
        "New York Knicks": "ny", "Oklahoma City Thunder": "okc", "Orlando Magic": "orl", "Philadelphia 76ers": "phi", "Phoenix Suns": "phx",
        "Portland Trail Blazers": "por", "Sacramento Kings": "sac", "San Antonio Spurs": "sa", "Toronto Raptors": "tor", "Utah Jazz": "utah",
        "Washington Wizards": "wsh"}

# ---------------- injury reports: latest status before a cut time
R = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(W, "research", "injury_history", "reports_*.csv.gz")))], ignore_index=True)
R = R[R.player.notna() & R.status.isin(["Out", "Doubtful", "Questionable", "Probable", "Available"])].copy()
R["date"] = pd.to_datetime(R.game_date, format="%m/%d/%Y").dt.strftime("%Y-%m-%d"); R["team_c"] = R.team.map(FULL)
R["name"] = R.player.map(lambda s: norm(" ".join(reversed([x.strip() for x in str(s).split(",", 1)])) if "," in str(s) else s))
R["as_of"] = pd.to_datetime(R.as_of)
snaps = {k: g.sort_values("as_of") for k, g in R.groupby(["date", "team_c"])}
say(f"injury report rows {len(R)}, team-dates {len(snaps)}")


def status_at(date, team, cut):
    g = snaps.get((date, team))
    if g is None: return {}
    g = g[g.as_of <= cut]
    if g.empty: return {}
    last = g[g.as_of == g.as_of.max()]
    return dict(zip(last.name, last.status))


# ---------------- features + v2 minutes
F = pd.read_csv(FEAT, dtype={"player_id": str, "game_id": str})
F = F[F.n_prev >= 3].copy(); F["d"] = pd.to_datetime(F.date)
for s in STATS: F[f"rhat_{s}"] = F[f"rate_{s}"] * F[f"allow_{s}"].fillna(1.0) * (F.pace if PACE[s] else 1.0)
F["home_c"] = np.where(F.home == 1, F.team, F.opp); F["away_c"] = np.where(F.home == 1, F.opp, F.team)
hist = F[["d", "team", "name", "min_proj"]].sort_values("d")


def v2_minutes(cut_fn):
    """per player-game: own status, M_out (teammates out/doubtful), minutes after redistribution. cut_fn(row) -> report cut time (ET)"""
    rows = []
    games = F[["date", "d", "team", "home_c", "away_c"]].drop_duplicates(["date", "team"])
    by_team = {t: g for t, g in hist.groupby("team")}
    by_day = {k: g[["name", "min_proj"]] for k, g in F.groupby(["date", "team"])}
    for gm in games.itertuples():
        cut = cut_fn(gm)
        st = status_at(gm.date, gm.team, cut)
        h = by_team[gm.team]; recent = h[(h.d < gm.d) & (h.d >= gm.d - pd.Timedelta(days=15))].drop_duplicates("name", keep="last")
        today = by_day[(gm.date, gm.team)]
        roster = pd.concat([recent[["name", "min_proj"]], today]).drop_duplicates("name", keep="last")
        out_ = roster[roster.name.map(lambda n: st.get(n) in ("Out", "Doubtful"))]
        rem = roster[~roster.name.isin(out_.name)]
        m_out = float(out_.min_proj.sum()); tot = float(rem.min_proj.sum()) or 1.0
        for r in today.itertuples():
            m2 = min(40.0, r.min_proj + m_out * r.min_proj / tot) if r.name in set(rem.name) else r.min_proj
            rows.append(dict(date=gm.date, team=gm.team, name=r.name, own=st.get(r.name, ""), m_out=m_out, min2=m2,
                             report=bool(st)))
    return pd.DataFrame(rows)


def tip_cut(bp):
    """report cut = scheduled tip (BettingPros, UTC) - 30 min, in ET; fallback 7 PM ET"""
    t = bp.drop_duplicates(["date", "home_c", "away_c"]).copy()
    t["cut"] = (pd.to_datetime(t.scheduled).dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.tz_localize(None) - pd.Timedelta(minutes=30))
    m = {}
    for r in t.itertuples(): m[(r.date, r.home_c)] = r.cut; m[(r.date, r.away_c)] = r.cut
    return lambda g: m.get((g.date, g.team), pd.Timestamp(g.date) + pd.Timedelta(hours=19))


BP = load_bp(W, books=["draftkings", "fanduel"])
BP = BP[BP.hours_before.between(-0.25, 6)]
say(f"BettingPros DK/FD close rows {len(BP)}, seasons {BP.season.value_counts().sort_index().to_dict()}")
M = v2_minutes(tip_cut(BP))
F2 = F.merge(M, on=["date", "team", "name"], how="left")
say(f"v2 minutes rows {len(M)}; with a report {M.report.mean()*100:.1f}%; mean minutes moved per team-game {M.groupby(['date','team']).m_out.first().mean():.1f}")

# alpha per stat on 2023-24 box only
A = {}
fb = F2[(F2.season == 2024) & (F2["min"] >= 15) & F2.m_out.notna()]
for s in STATS:
    # weighted by the expected count e = minutes x projected rate (players who rarely shoot threes would otherwise blow it up):
    # alpha = sum x (actual - e) / sum e x^2   (written before any prop result; see the pre-registration note)
    x = fb.m_out / 240; e = fb["min"] * fb[f"rhat_{s}"]
    A[s] = float((x * (fb[s] - e)).sum() / (e * x ** 2).sum())
say("usage bump alpha (2023-24 box only): " + ", ".join(f"{k} {v:+.3f}" for k, v in A.items()))
for s in STATS:
    F2[f"mu2_{s}"] = F2.min2.fillna(F2.min_proj) * F2[f"rhat_{s}"] * (1 + A[s] * F2.m_out.fillna(0) / 240)
    F2[f"mu1_{s}"] = F2[f"mu_{s}"]


def nb_p_over(mu, stat, line):
    a, b = P1["var_ab"][stat]; mu = np.clip(mu, 0.05, None); ex = (a - 1) * mu + b * mu ** 2
    r = np.where(ex > 1e-6, mu ** 2 / np.clip(ex, 1e-6, None), 1e6)
    return 1 - stats.nbinom.cdf(np.floor(line), r, r / (r + mu))


# ---------------- tests A (BettingPros closes)
key = ["date", "home_c", "away_c", "name", "stat"]
Pv = BP.pivot_table(index=key + ["book", "season"], columns="side", values=["line", "price"], aggfunc="first")
Pv.columns = [f"{a}_{b}" for a, b in Pv.columns]; Pv = Pv.reset_index()
Pv = Pv[(Pv.line_over == Pv.line_under)].rename(columns={"line_over": "line"}).drop(columns="line_under")
qo, qu = 1 / dec(Pv.price_over), 1 / dec(Pv.price_under); Pv["fair_over"] = qo / (qo + qu)
mk = Pv[Pv.book == "draftkings"].set_index(key)[["line", "fair_over"]].combine_first(Pv[Pv.book == "fanduel"].set_index(key)[["line", "fair_over"]])
mk = mk.rename(columns={"line": "mline", "fair_over": "p_close"}).reset_index()
long = []
for s in STATS:
    long.append(F2[["season", "date", "home_c", "away_c", "name", "own", "min_proj", "min2", "m_out", s, f"mu1_{s}", f"mu2_{s}"]]
                .rename(columns={s: "actual", f"mu1_{s}": "mu1", f"mu2_{s}": "mu2"}).assign(stat=s))
FL = pd.concat(long, ignore_index=True)
X = Pv.merge(mk, on=key).merge(FL, on=["date", "home_c", "away_c", "name", "stat"], how="inner", suffixes=("", "_f"))
X = X[X.line == X.mline]
for s in STATS:
    m = X.stat == s
    X.loc[m, "p1"] = nb_p_over(X.loc[m, "mu1"].values, s, X.loc[m, "line"].values)
    X.loc[m, "p2"] = nb_p_over(X.loc[m, "mu2"].values, s, X.loc[m, "line"].values)
X["y"] = np.where(X.actual > X.line, 1.0, np.where(X.actual < X.line, 0.0, np.nan))
G = X.drop_duplicates(key)                      # one row per player-stat-game for model/market tests
lg = lambda p: np.log(np.clip(p, 0.01, 0.99) / (1 - np.clip(p, 0.01, 0.99)))
say(f"test rows (player-stat-games with DK/FD close at the same line): {G.season.value_counts().sort_index().to_dict()}")

def info_test(d, pcol):
    d = d[d.y.notna()]; Xm = np.column_stack([np.ones(len(d)), lg(d.p_close), lg(d[pcol]) - lg(d.p_close)])
    nll = lambda b: -np.mean(d.y * (Xm @ b) - np.log1p(np.exp(Xm @ b)))
    b = optimize.minimize(nll, [0, 1, 0], method="BFGS").x; p = 1 / (1 + np.exp(-Xm @ b))
    se = np.sqrt(np.diag(np.linalg.inv((Xm * (p * (1 - p))[:, None]).T @ Xm)))
    return b, se, len(d)

def fit_w(d, pcol):
    d = d[d.y.notna()]
    ll = lambda w: -np.mean(d.y * np.log(np.clip(w * d[pcol] + (1 - w) * d.p_close, 1e-6, 1)) + (1 - d.y) * np.log(np.clip(1 - (w * d[pcol] + (1 - w) * d.p_close), 1e-6, 1)))
    w = float(optimize.minimize_scalar(ll, bounds=(0, 1), method="bounded").x); return w, ll(0), ll(1), ll(w)

def boot(df, col, n=3000):
    g = df.groupby("date")[col].agg(["sum", "count"]).values
    if len(g) < 5: return np.nan, np.nan
    idx = rng.integers(0, len(g), (n, len(g))); m = g[idx, 0].sum(1) / g[idx, 1].sum(1)
    return np.percentile(m, 5), np.percentile(m, 95)

res = {}
for ver, pcol in (("v2", "p2"), ("v1b", "p1")):
    Fi = G[G.season == FIT]
    if len(Fi) < 500: say(f"{ver}: only {len(Fi)} fit rows; skipping"); continue
    w, l0, l1, lw = fit_w(Fi, pcol)
    say(f"\n== {ver} == FIT 2023-24 blend weight w {w:.3f} (log loss close {l0:.4f}, model {l1:.4f}, blend {lw:.4f}, n {len(Fi)})")
    X["p"] = w * X[pcol] + (1 - w) * X.p_close
    cand = []
    for side in ("over", "under"):
        ps = X.p if side == "over" else 1 - X.p
        cand.append(X.assign(side=side, price=X[f"price_{side}"], ev=ps * dec(X[f"price_{side}"]) - 1))
    C = pd.concat(cand).sort_values("ev", ascending=False).drop_duplicates(key + ["side"]).drop_duplicates(key)
    if ver == "v2": C = C[~C.own.isin(["Out", "Doubtful", "Questionable"])]
    won = np.where(C.side == "over", C.actual > C.line, C.actual < C.line)
    C["u"] = np.where(C.actual == C.line, 0.0, np.where(won, dec(C.price) - 1, -1.0))
    for season, lab in ((FIT, "fit 2023-24"), (TEST_A, "TEST A 2024-25"), (2026, "2025-26 (descriptive)"), (2023, "2022-23 (descriptive)")):
        T = G[G.season == season]
        if len(T) < 300: continue
        b, se, n = info_test(T, pcol)
        Bt = C[(C.season == season) & (C.ev >= 0.05)]
        lo, hi = boot(Bt, "u") if len(Bt) else (np.nan, np.nan)
        say(f"  {lab}: model-beyond-close coef {b[2]:+.3f} (se {se[2]:.3f}, 90% [{b[2]-1.645*se[2]:+.3f}, {b[2]+1.645*se[2]:+.3f}]), close over-lean {b[0]:+.3f}, n {n} | "
            f"bets {len(Bt)}, win {(Bt.u > 0).sum() / max((Bt.u != 0).sum(), 1)*100:.1f}%, {Bt.u.sum():+.1f}u, ROI {Bt.u.mean()*100 if len(Bt) else float('nan'):+.1f}% [{lo*100:+.1f}, {hi*100:+.1f}]")
        if season == TEST_A: res[ver] = (b[2] - 1.645 * se[2] > 0) and Bt.u.sum() > 0
    C.assign(version=ver).to_csv(os.path.join(W, "analysis", f"props_{ver}_close_bets.csv.gz"), index=False)

say("\n== Verdict (Test A, pre-registered: v2 only) ==")
if "v2" in res: say(f"v2: {'PASS -> PROVISIONAL after Fable check' if res['v2'] else 'did not pass'}" + ("" if (G.season == TEST_A).sum() > 5000 else "  (NOT FINAL: 2024-25 still downloading)"))
say("v1b on the same rows is shown for comparison only.")
open(os.path.join(W, "analysis", "props_v2_output.txt"), "w").write("\n".join(out) + "\n")
