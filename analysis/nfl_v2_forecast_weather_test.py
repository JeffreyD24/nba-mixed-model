"""NFL totals v2 with FORECAST weather, graded at the DraftKings total posted when the forecast existed (2022-25). Nov 4, 2026.
Pre-registration: nfl-mixed-model backtests/WEATHER_FORECAST_V2_PREREG.md (pushed in commit 72a75ed before this ran).
v2 is built exactly as analysis/nfl_weather_leak_test.py (its code up to the grading is executed unchanged); only the weather INPUTS of the
graded games are swapped for forecasts, and the line is the DraftKings total at kickoff - L days.
  python analysis/nfl_v2_forecast_weather_test.py WORKDIR NFL_REPO  -> analysis/nfl_v2_forecast_weather_test_output.txt"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])

# 1. v2 build, unchanged
src = open(os.path.join(W, "analysis", "nfl_weather_leak_test.py")).read().split("\nout = []")[0].split(
    "W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])", 1)[1]
exec(src)

out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

# 2. coefficients per test season (same fits as the leak test), kept so other weather inputs can be fed in
TEST = [2022, 2023, 2024, 2025]
pcoef = {s: fit(Gp[(Gp.season < s) & (Gp.season >= 2018)], TF_W, "total_y") for s in TEST}
pcoef_n = {s: fit(Gp[(Gp.season < s) & (Gp.season >= 2018)], TF_N, "total_y") for s in TEST}
tcoef = {}
for s in TEST:
    tr = P.season != s   # leave-season-out, as adjust() in the leak test
    tcoef[s] = np.linalg.lstsq(P.loc[tr, ["wind_x", "cold_x"]].values, (P.tp - P.pt)[tr].values, rcond=None)[0]

# player-model rows for the test games (features without weather)
Gt = Gp[Gp.season.isin(TEST)].drop_duplicates(["date", "home", "away"])[["date", "home", "away"] + [c for c in TF_N if c != "one"]]
D = P[P.season.isin(TEST) & P.week.between(5, 14)].merge(Gt, on=["date", "home", "away"], how="inner")
D["one"] = 1.0
assert not [c for c in D.columns if c.endswith(("_x_", "_y"))], "merge collision"

# 3. forecasts, keyed to date/home/away through nflverse game ids
V2 = pd.read_csv(os.path.join(N, "data", "nflverse_games.csv"))
V2["home"] = V2.home_team.map(code); V2["away"] = V2.away_team.map(code); V2["date"] = V2.gameday
V2["outdoor"] = V2.roof.isin(["outdoors", "open"])
V2["kick_utc"] = (pd.to_datetime(V2.gameday + " " + V2.gametime.fillna("13:00"))
                  .dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC"))
NB = pd.read_csv(os.path.join(N, "data", "external", "weather_forecasts", "nfl_iem_nbm_2022_2025.csv"))
nbw = NB.pivot_table(index="game_id", columns="days_before", values="wind_mph")
OM = pd.read_csv(os.path.join(N, "data", "external", "weather_forecasts", "nfl_forecasts_2022_2025.csv"))
omt = OM.pivot_table(index="game_id", columns="days_before", values="temp_f")
V2 = V2.set_index("game_id")
for L in (1, 5, 7):
    V2[f"fw{L}"] = nbw[L] if L in nbw.columns else np.nan
for L in (1, 6):
    V2[f"ft{L}"] = omt[L] if L in omt.columns else np.nan
V2 = V2.reset_index()
D = D.merge(V2[["date", "home", "away", "kick_utc", "fw1", "fw5", "fw7", "ft1", "ft6"]].rename(columns={"outdoor": "od"}),
            on=["date", "home", "away"], how="left")
D["od"] = D.outdoor.fillna(False).astype(bool)

# 4. DraftKings total at kickoff - L days (as nfl_wind_forecast_test.py)
snaps = []
for f in sorted(glob.glob(os.path.join(W, "data", "odds_history", "nfl", "*.csv.gz"))):
    if f.split(os.sep)[-1][:4] not in ("2022", "2023", "2024", "2025", "2026"): continue
    d = pd.read_csv(f); d = d[(d.book == "draftkings") & (d.market == "totals") & (d.outcome == "Over")]
    if len(d): snaps.append(d[["snapshot_utc", "commence_et", "home", "away", "point"]])
S = pd.concat(snaps); S["t"] = pd.to_datetime(S.snapshot_utc, utc=True)
S["tip"] = pd.to_datetime(S.commence_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
S = S[S.t < S.tip].sort_values("t")
NAME = {"Arizona Cardinals": "ari", "Atlanta Falcons": "atl", "Baltimore Ravens": "bal", "Buffalo Bills": "buf", "Carolina Panthers": "car",
        "Chicago Bears": "chi", "Cincinnati Bengals": "cin", "Cleveland Browns": "cle", "Dallas Cowboys": "dal", "Denver Broncos": "den",
        "Detroit Lions": "det", "Green Bay Packers": "gb", "Houston Texans": "hou", "Indianapolis Colts": "ind", "Jacksonville Jaguars": "jax",
        "Kansas City Chiefs": "kc", "Los Angeles Chargers": "lac", "Los Angeles Rams": "lar", "Las Vegas Raiders": "lv", "Miami Dolphins": "mia",
        "Minnesota Vikings": "min", "New England Patriots": "ne", "New Orleans Saints": "no", "New York Giants": "nyg", "New York Jets": "nyj",
        "Philadelphia Eagles": "phi", "Pittsburgh Steelers": "pit", "Seattle Seahawks": "sea", "San Francisco 49ers": "sf", "Tampa Bay Buccaneers": "tb",
        "Tennessee Titans": "ten", "Washington Commanders": "wsh"}
S["h"] = S.home.map(NAME); S["a"] = S.away.map(NAME); S["date"] = S.tip.dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
idx = {k: g for k, g in S.groupby(["date", "h", "a"])}
def line_at(r, L):
    g = idx.get((r.date, r.home, r.away))
    if g is None or pd.isna(r.kick_utc): return np.nan
    cut = r.kick_utc - pd.Timedelta(days=L); g = g[g.t <= cut]
    if not len(g) or (cut - g.t.iloc[-1]) > pd.Timedelta(hours=24): return np.nan
    return float(g.point.iloc[-1])
first = S.groupby(["date", "h", "a"]).t.min()
D["first_lead_d"] = [(r.kick_utc - first.get((r.date, r.home, r.away), pd.NaT)).total_seconds() / 86400 if pd.notna(r.kick_utc) else np.nan
                     for r in D.itertuples()]

# 5. v2 numbers for any weather input
def v2(wind, cold):
    out_ = np.full(len(D), np.nan)
    for s in TEST:
        m = (D.season == s).values
        Xp = D.loc[m, TF_N].copy(); Xp["wind_x"] = wind[m]; Xp["cold_x"] = cold[m]
        player = Xp[TF_W].values @ pcoef[s]
        team = D.pt.values[m] + np.c_[wind[m], cold[m]] @ tcoef[s]
        out_[m] = (team + player) / 2
    return out_
def v2_none():
    out_ = np.full(len(D), np.nan)
    for s in TEST:
        m = (D.season == s).values
        out_[m] = (D.pt.values[m] + D.loc[m, TF_N].values @ pcoef_n[s]) / 2
    return out_
od = D.od.values
def wx(col_w, col_t):
    w = np.where(od, D[col_w].values, 0.0); med = np.nanmedian(D.loc[od, col_w]); w = np.where(od & np.isnan(w), med, w)
    t = D[col_t].values; c = np.where(od, np.clip(40 - np.where(np.isnan(t), 60, t), 0, None), 0.0)
    return w, c
REC = (D.wind_x.values, D.cold_x.values)
NONE = v2_none()

rng = np.random.default_rng(20261104)
def units(pred, line):
    e = pred - line
    bet = (np.abs(e) >= 2) & ~np.isnan(line) & ~np.isnan(e)
    r = np.sign(e) * (D.tp.values - line)
    u = np.where(bet, np.where(r > 0, 100 / 110, np.where(r < 0, -1.0, 0.0)), 0.0)
    return bet, r, u
def summary(lab, pred, line):
    e = pred - line; bet, r, u = units(pred, line); w = int(((r > 0) & bet).sum()); l = int(((r < 0) & bet).sum())
    clv = np.nanmean((np.sign(e) * (D.c_tot.values - line))[bet]) if bet.any() else np.nan
    per = " ".join(f"{s % 100}:{u[(D.season == s).values].sum():+.1f}" for s in TEST)
    say(f"  {lab:34s} {w + l:4d} bets {w / max(w + l, 1):.1%} {u.sum():+6.1f}u  CLV {clv:+.2f} pts   [{per}]")
    return u
days = D.date.values; ud = np.unique(days); pos = {d: np.where(days == d)[0] for d in ud}
def boot(diff):
    sums = np.array([diff[pos[d]].sum() for d in ud]); B = rng.integers(0, len(ud), (10000, len(ud)))
    bs = sums[B].sum(1); return diff.sum(), np.percentile(bs, 5), np.percentile(bs, 95)

say("NFL totals v2 with forecast weather, DraftKings totals 2022-25, weeks 5-14, edge 2+ (pre-registered: WEATHER_FORECAST_V2_PREREG.md)")
say(f"games: {len(D)} (outdoor {od.sum()}); first DraftKings total snapshot: median {np.nanmedian(D.first_lead_d):.1f} days before kickoff, "
    f"{(D.first_lead_d > 7).mean():.0%} posted more than 7 days ahead (before any forecast we hold)")
say()
say("At the opener (no forecast exists yet for most games):")
summary("no weather", NONE, D.o_tot.values)
summary("recorded game-time weather (LEAKS)", v2(*REC), D.o_tot.values)
for L, tcol, lab in ((7, "ft6", "7 days"), (5, "ft6", "5 days  [PRIMARY]"), (1, "ft1", "1 day")):
    line = np.array([line_at(r, L) for r in D.itertuples()])
    fw, fc = wx(f"fw{L}", tcol); FC = v2(fw, fc)
    say(); say(f"Line = DraftKings total {lab} before kickoff ({np.isfinite(line).sum()} games have one)")
    uf = summary(f"forecast weather ({L} d)", FC, line)
    un = summary("no weather", NONE, line)
    summary("recorded weather (LEAKS)", v2(*REC), line)
    est, lo, hi = boot(uf - un)
    say(f"  forecast minus no weather: {est:+.1f}u  90% interval {lo:+.1f} to {hi:+.1f}  (game-day bootstrap)")
    say(f"  bets that differ: forecast-only {int(((np.abs(FC - line) >= 2) & ~(np.abs(NONE - line) >= 2)).sum())}, "
        f"no-weather-only {int((~(np.abs(FC - line) >= 2) & (np.abs(NONE - line) >= 2)).sum())}")
    if L == 5:
        verdict = "ADDS VALUE" if lo > 0 else ("consistent, not confirmed" if est > 0 else "not shown")
        say(f"  PRIMARY verdict (lead 5 d): {verdict}")
open(os.path.join(W, "analysis", "nfl_v2_forecast_weather_test_output.txt"), "w").write("\n".join(out) + "\n")
