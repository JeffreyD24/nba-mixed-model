"""Wind-forecast test for NFL totals, 2022-25 (Nov 3, 2026). Follow-up to the leakage audit and the wind test in data_jobs_status_2026-11-03.md.
Question: does a wind FORECAST available around the opener explain the game total relative to DraftKings' OPENING total, and does the market
move the total toward it by the close?  (Earlier test: 2024-25 only, 348 games, graded against one close-ish line; day-6 wind t = -2.3 but with
opposite signs in 2024 and 2025, so not reliable.)
Data: NBM station forecasts (nfl-mixed-model data/external/weather_forecasts/nfl_iem_nbm_2022_2025.csv: wind/gust mph, NBS lead 1 d, NBE leads 5/6/7 d),
DraftKings open/close totals (nba-mixed-model data/odds_history/nfl_open_close.csv; open_spread_t = when the opener posted), final scores and recorded wind (nflverse).
The forecast lead used = the NBE lead (5, 6 or 7 d) nearest to how long before kickoff DraftKings' opener posted, clipped to 5-7.
Outdoor / open-roof home-site regular-season games only (the games that have forecasts). Seeded bootstrap, resampling games.
  python analysis/nfl_wind_forecast_test.py WORKDIR NFL_REPO  -> analysis/nfl_wind_forecast_test_output.txt"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
out = []
def say(*a):
    out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
rng = np.random.default_rng(20261103)

G = pd.read_csv(os.path.join(N, "data", "nflverse_games.csv"))
G = G[(G.game_type == "REG") & G.season.between(2022, 2025)].copy()
G["kick_utc"] = (pd.to_datetime(G.gameday + " " + G.gametime.fillna("13:00")).dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward")
                 .dt.tz_convert("UTC"))
CODE = {"LA": "lar", "LV": "lv", "OAK": "lv", "WAS": "wsh"}
G["h"] = G.home_team.map(lambda t: CODE.get(t, t.lower())); G["a"] = G.away_team.map(lambda t: CODE.get(t, t.lower()))
G["pts"] = G.home_score + G.away_score
G["wind_rec"] = pd.to_numeric(G.wind, errors="coerce")

F = pd.read_csv(os.path.join(N, "data", "external", "weather_forecasts", "nfl_iem_nbm_2022_2025.csv"))
wide = F.pivot_table(index="game_id", columns="days_before", values=["wind_mph", "gust_mph"]).copy()
wide.columns = [f"{a.split('_')[0]}_f{b}" for a, b in wide.columns]
wide = wide.reset_index()

O = pd.read_csv(os.path.join(W, "data", "odds_history", "nfl_open_close.csv"))
O = O[O.book == "draftkings"].dropna(subset=["open_total", "close_total"]).copy()
O["open_t"] = pd.to_datetime(O.open_spread_t, utc=True)
O = O.drop_duplicates(["date", "home", "away"])

D = G.merge(wide, on="game_id", how="inner").merge(O[["date", "home", "away", "open_total", "close_total", "open_t"]],
                                                   left_on=["gameday", "h", "a"], right_on=["date", "home", "away"], how="inner")
D["lead_open_d"] = (D.kick_utc - D.open_t).dt.total_seconds() / 86400
D["lead_use"] = D.lead_open_d.round().clip(5, 7).astype(int)
D["wind_m"] = np.where(D.lead_use == 5, D.wind_f5, np.where(D.lead_use == 6, D.wind_f6, D.wind_f7))
D["gust_m"] = np.where(D.lead_use == 5, D.gust_f5, np.where(D.lead_use == 6, D.gust_f6, D.gust_f7))
D["err_open"] = D.pts - D.open_total; D["move"] = D.close_total - D.open_total; D["err_close"] = D.pts - D.close_total
say(f"games: outdoor home-site REG 2022-25 with forecasts {G.game_id.isin(wide.game_id).sum()}, matched to DraftKings opener {len(D)} "
    f"({D.groupby('season').size().to_dict()})")
say(f"opener posted how many days before kickoff: median {D.lead_open_d.median():.1f}, 10th-90th pct {D.lead_open_d.quantile(.1):.1f}-{D.lead_open_d.quantile(.9):.1f}; "
    f"forecast lead used: {D.lead_use.value_counts().sort_index().to_dict()}")
say(f"mean total {D.pts.mean():.1f}, mean opener {D.open_total.mean():.1f}, mean (total - opener) {D.err_open.mean():+.2f}, mean line move open->close {D.move.mean():+.2f}")
say()

def ols(x, y):
    m = x.notna() & y.notna(); x, y = x[m].values.astype(float), y[m].values.astype(float)
    X = np.c_[np.ones(len(x)), x]; b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b
    V = np.linalg.inv(X.T @ X) @ (X.T * e ** 2) @ X @ np.linalg.inv(X.T @ X)           # HC0 robust
    return b[1], b[1] / np.sqrt(V[1, 1]), int(m.sum())
def boot_slope(x, y, B=4000):
    m = x.notna() & y.notna(); x, y = x[m].values.astype(float), y[m].values.astype(float); n = len(x); s = []
    for _ in range(B):
        i = rng.integers(0, n, n); xi, yi = x[i], y[i]
        s.append(np.cov(xi, yi, bias=True)[0, 1] / max(xi.var(), 1e-9))
    return np.percentile(s, [5, 95])

say("1. Slopes (points per mph of forecast wind), pooled 2022-25; t = robust t-stat; [90% bootstrap range]")
say(f"{'predictor':28s} {'y = total - OPENER':>34s} {'y = move open->close':>34s} {'y = total - CLOSE':>34s}")
preds = [("forecast wind, lead matched to opener", "wind_m"), ("forecast gust, lead matched", "gust_m"), ("forecast wind, 5 d", "wind_f5"),
         ("forecast wind, 6 d", "wind_f6"), ("forecast wind, 7 d", "wind_f7"), ("forecast wind, 1 d", "wind_f1"), ("recorded game wind", "wind_rec")]
for lab, c in preds:
    cells = []
    for yv in ("err_open", "move", "err_close"):
        b, t, n = ols(D[c], D[yv]); lo, hi = boot_slope(D[c], D[yv], 1500)
        cells.append(f"{b:+.3f} (t {t:+.1f}) [{lo:+.2f},{hi:+.2f}] n{n}")
    say(f"{lab:28s} {cells[0]:>34s} {cells[1]:>34s} {cells[2]:>34s}")
say()
say("2. By season, forecast wind (lead matched) -> total - opener / move open->close  (slope, t, n)")
for s, d in D.groupby("season"):
    b1, t1, n1 = ols(d.wind_m, d.err_open); b2, t2, n2 = ols(d.wind_m, d.move)
    say(f"  {s}: total-opener {b1:+.3f} (t {t1:+.1f}), move {b2:+.3f} (t {t2:+.1f}), n={n1}")
say(f"  2022-23 only: total-opener {ols(D[D.season<=2023].wind_m, D[D.season<=2023].err_open)[0]:+.3f} (t {ols(D[D.season<=2023].wind_m, D[D.season<=2023].err_open)[1]:+.1f}); "
    f"2024-25 only: {ols(D[D.season>=2024].wind_m, D[D.season>=2024].err_open)[0]:+.3f} (t {ols(D[D.season>=2024].wind_m, D[D.season>=2024].err_open)[1]:+.1f})")
say()
say("3. Bins of forecast wind (lead matched): mean total - opener, mean move, over rate vs opener (pushes dropped)")
D["bin"] = pd.cut(D.wind_m, [-1, 8, 12, 16, 100], labels=["<8", "8-12", "12-16", "16+"])
for b, d in D.groupby("bin", observed=True):
    nz = d[d.err_open != 0]
    say(f"  {b:>6s} mph: n={len(d):3d}  total-opener {d.err_open.mean():+6.2f}  move {d.move.mean():+5.2f}  over {100*(nz.err_open>0).mean():.1f}%  mean recorded wind {d.wind_rec.mean():.1f}")
say()

def grade(m, side):
    d = D[m]; sg = -1 if side == "under" else 1
    r = sg * d.err_open; w, l = int((r > 0).sum()), int((r < 0).sum()); u = w * 100 / 110 - l
    clv = (sg * (d.close_total - d.open_total)).mean()
    n = w + l; roi = []
    rr = np.where(r > 0, 100 / 110, np.where(r < 0, -1.0, 0.0))
    for _ in range(3000): roi.append(rng.choice(rr, len(rr)).mean())
    return n, w / max(n, 1), u, clv, np.percentile(roi, [5, 95])
say("4. Rule test: bet the UNDER at the DraftKings opener (-110) when forecast wind (lead matched) >= X mph. No tuning: X = 10, 12, 15 all shown.")
for X in (10, 12, 15):
    m = D.wind_m >= X; n, wp, u, clv, ci = grade(m, "under")
    per = " ".join(f"{s % 100}:{grade(m & (D.season == s), 'under')[2]:+.1f}" for s in (2022, 2023, 2024, 2025))
    say(f"  wind >= {X:2d}: {n:3d} bets {wp:.1%} {u:+6.1f}u  ROI {100*u/max(n,1):+5.1f}% [90% {100*ci[0]:+.1f}, {100*ci[1]:+.1f}]  CLV {clv:+.2f} pts (positive = total fell after the open)   by season {per}")
say("  same rule with RECORDED game wind (a leak: unknown at the open):")
for X in (10, 15):
    m = D.wind_rec >= X; n, wp, u, clv, ci = grade(m, "under")
    say(f"  recorded wind >= {X:2d}: {n:3d} bets {wp:.1%} {u:+6.1f}u  ROI {100*u/max(n,1):+5.1f}% [90% {100*ci[0]:+.1f}, {100*ci[1]:+.1f}]  CLV {clv:+.2f} pts")

# ---------------------------------------------------------------------------------------------------------------------------------
# 5. Leak-safe version: grade each forecast against the DraftKings total that was POSTED when that forecast was issued.
#    DraftKings' first line comes out ~12 days ahead, before any usable forecast, so grading a 7-day forecast against the opener credits it with
#    information the opener did not have. Here: line_L = last DraftKings total snapshot at or before (kickoff - L days), at most 24 h stale.
say(); say("5. LEAK-SAFE: forecast issued L days ahead vs the DraftKings total posted at that moment (snapshots every ~3 h)")
import glob
snaps = []
for f in sorted(glob.glob(os.path.join(W, "data", "odds_history", "nfl", "*.csv.gz"))):
    y = f.split(os.sep)[-1][:4]
    if y not in ("2022", "2023", "2024", "2025", "2026"): continue
    d = pd.read_csv(f)
    d = d[(d.book == "draftkings") & (d.market == "totals") & (d.outcome == "Over")]
    if len(d): snaps.append(d[["snapshot_utc", "event_id", "commence_et", "home", "away", "point"]])
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
first = S.groupby(["date", "h", "a"]).t.min().reset_index().rename(columns={"t": "first_t"})
D = D.merge(first, left_on=["gameday", "h", "a"], right_on=["date", "h", "a"], how="left", suffixes=("", "_s"))
D["first_snap_lead_d"] = (D.kick_utc - D.first_t).dt.total_seconds() / 86400
say(f"first DraftKings total snapshot is {D.first_snap_lead_d.median():.1f} days before kickoff (median; 10th-90th {D.first_snap_lead_d.quantile(.1):.1f}-{D.first_snap_lead_d.quantile(.9):.1f}); "
    f"the 'opener' in nfl_open_close.csv is the first snapshot, so it is NOT necessarily the day DraftKings posted it")
idx = {k: g for k, g in S.groupby(["date", "h", "a"])}
def line_at(row, L):
    g = idx.get((row.gameday, row.h, row.a))
    if g is None: return np.nan
    cut = row.kick_utc - pd.Timedelta(days=L); g = g[g.t <= cut]
    if not len(g) or (cut - g.t.iloc[-1]) > pd.Timedelta(hours=24): return np.nan
    return float(g.point.iloc[-1])
MOS = pd.read_csv(os.path.join(N, "data", "external", "weather_forecasts", "nfl_iem_mos_2022_2025.csv"))
m3 = MOS[MOS.days_before == 3].set_index("game_id").wind_mph
D["wind_f3"] = D.game_id.map(m3)
LEADS = [("7 d", 7, "wind_f7"), ("5 d", 5, "wind_f5"), ("3 d", 3, "wind_f3"), ("1 d", 1, "wind_f1")]
for lab, L, c in LEADS:
    D[f"line_{L}"] = [line_at(r, L) for r in D.itertuples()]
    D[f"err_{L}"] = D.pts - D[f"line_{L}"]
say(f"games with a DraftKings total posted within 24 h before each lead: " + ", ".join(f"{lab} {int(D[f'line_{L}'].notna().sum())}" for lab, L, c in LEADS))
say(f"{'forecast issued':16s} {'slope: total - line then (t) [90% boot]':44s} {'within-stadium slope (t)':28s} {'move: close - line then (t)':30s}")
for lab, L, c in LEADS:
    x, yv = D[c], D[f"err_{L}"]
    b, t, n = ols(x, yv); lo, hi = boot_slope(x, yv, 1500)
    xw = x - D.groupby("home_team")[c].transform("mean")                    # remove each stadium's average wind: day-to-day weather only
    bw, tw, nw = ols(xw, yv)
    mv = D.close_total - D[f"line_{L}"]; bm, tm, nm = ols(x, mv)
    say(f"{lab:16s} {b:+.3f} (t {t:+.1f}) [{lo:+.2f},{hi:+.2f}] n{n:<4d}      {bw:+.3f} (t {tw:+.1f})          {bm:+.3f} (t {tm:+.1f})")
say()
say("Rule at each lead, graded at the line posted then (no tuning): UNDER when forecast wind >= X mph, -110. [90% ROI range], CLV = how far the total fell by the close")
def grade2(mask, L):
    d = D[mask]; r = -(d[f"err_{L}"]); rr = np.where(r > 0, 100 / 110, np.where(r < 0, -1.0, 0.0)); w, l = int((r > 0).sum()), int((r < 0).sum())
    if not len(rr): return 0, 0, 0, 0, (0, 0)
    ci = np.percentile([rng.choice(rr, len(rr)).mean() for _ in range(3000)], [5, 95]); u = w * 100 / 110 - l
    return w + l, w / max(w + l, 1), u, (d[f"line_{L}"] - d.close_total).mean(), ci
for lab, L, c in LEADS:
    for X in (10, 12, 15):
        mk = D[c].ge(X) & D[f"line_{L}"].notna(); n, wp, u, clv, ci = grade2(mk, L)
        per = " ".join(f"{s % 100}:{grade2(mk & (D.season == s), L)[2]:+.1f}" for s in (2022, 2023, 2024, 2025))
        say(f"  {lab} forecast >= {X:2d}: {n:3d} bets {wp:5.1%} {u:+6.1f}u ROI {100*u/max(n,1):+6.1f}% [{100*ci[0]:+.0f},{100*ci[1]:+.0f}]  CLV {clv:+.2f}  by season {per}")


say()
say("6. Same rule graded at the CLOSING total (-110): is the wind effect still there when the market has finished moving?")
for lab, L, c in LEADS:
    for X in (10, 12, 15):
        mk = D[c].ge(X); d = D[mk]; r = -(d.pts - d.close_total); rr = np.where(r > 0, 100 / 110, np.where(r < 0, -1.0, 0.0)); w, l = int((r > 0).sum()), int((r < 0).sum())
        if not len(rr): continue
        ci = np.percentile([rng.choice(rr, len(rr)).mean() for _ in range(3000)], [5, 95]); u = w * 100 / 110 - l
        per = " ".join(f"{s_ % 100}:{(lambda dd: ((-(dd.pts - dd.close_total) > 0).sum() * 100 / 110 - (-(dd.pts - dd.close_total) < 0).sum()))(d[d.season == s_]):+.1f}" for s_ in (2022, 2023, 2024, 2025))
        say(f"  {lab} forecast >= {X:2d} at the close: {w + l:3d} bets {w / max(w + l, 1):5.1%} {u:+6.1f}u ROI {100 * u / max(w + l, 1):+6.1f}% [{100 * ci[0]:+.0f},{100 * ci[1]:+.0f}]  by season {per}")
say("  slope of (total - closing total) on forecast wind, by season, 1 d forecast: " + ", ".join(f"{s_}: {ols(g.wind_f1, g.err_close)[0]:+.2f} (t {ols(g.wind_f1, g.err_close)[1]:+.1f})" for s_, g in D.groupby("season")))

open(os.path.join(W, "analysis", "nfl_wind_forecast_test_output.txt"), "w").write("\n".join(out) + "\n")
