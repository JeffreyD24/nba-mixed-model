"""Step 2 of the NFL timing test (pre-registration: nfl-mixed-model backtests/TIMING_PREREG.md, commit 9078e64).
Totals v2 as known at T1 (first DraftKings total), T2 (Monday 9 AM before week k), T3 (Tuesday 11:45 AM, current live lock),
graded at the DraftKings total posted at that moment. Needs analysis/nfl_timing_team.py's outputs.
  python analysis/nfl_timing_test.py WORKDIR NFL_REPO  -> analysis/nfl_timing_test_output.txt, analysis/nfl_timing_bets.csv"""
import os, sys, glob
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
ET = "America/New_York"

# 1. v2 build from the leak test, unchanged (gives Gp, fit, TF_W, TF_N, P, code)
src = open(os.path.join(W, "analysis", "nfl_weather_leak_test.py")).read().split("\nout = []")[0].split(
    "W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])", 1)[1]
exec(src)
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

SEAS = list(range(2020, 2026))
pcoef = {s: fit(Gp[(Gp.season < s) & (Gp.season >= 2018)], TF_W, "total_y") for s in SEAS}
pcoef_n = {s: fit(Gp[(Gp.season < s) & (Gp.season >= 2018)], TF_N, "total_y") for s in SEAS}
tcoef = {s: np.linalg.lstsq(P.loc[P.season != s, ["wind_x", "cold_x"]].values, (P.tp - P.pt)[P.season != s].values, rcond=None)[0] for s in SEAS}

# 2. games, cutoffs, team-model numbers at each timing
C = pd.read_csv(os.path.join(W, "analysis", "nfl_timing_cutoffs.csv"))
for c in ("kick", "T1", "T2", "T3"): C[c] = pd.to_datetime(C[c], utc=True).dt.tz_convert(ET)
TM = pd.read_csv(os.path.join(W, "analysis", "nfl_timing_team_preds.csv"))
TM = TM[TM["T"] != "T0"].pivot_table(index="game_id", columns="T", values="tm_total")
TM.columns = [f"team_{c}" for c in TM.columns]
D = C[C.week.between(5, 14)].merge(TM.reset_index(), on="game_id", how="left")
R = pd.read_csv(os.path.join(N, "data", "nflverse_games.csv"))[["game_id", "home_score", "away_score", "roof"]]
D = D.merge(R, on="game_id", how="left"); D["tp"] = D.home_score + D.away_score
D["od"] = D.roof.isin(["outdoors", "open"])

# 3. player features as of each cutoff: each team's pre-game row for its first regular-season game on or after the cutoff date
F = pd.read_csv(os.path.join(N, "data", "player_team_games.csv")); F = F[F.stype == "REG"].copy()
F["date"] = pd.to_datetime(F.date); F = F.sort_values("date")
k = ["qb_epa", "rush_off", "pass_def", "rush_def", "plays", "qb_change"]
by_team = {t: g.reset_index(drop=True) for t, g in F.groupby("team")}
def feats(team, cut_day):
    g = by_team.get(team)
    if g is None: return None
    i = g.date.searchsorted(cut_day)
    return None if i >= len(g) else g.loc[i, k]
def player_inputs(T):
    rows = []
    for r in D.itertuples():
        t = getattr(r, T)
        if pd.isna(t): rows.append([np.nan] * 4); continue
        cd = pd.Timestamp(t.strftime("%Y-%m-%d")); h = feats(r.h, cd); a = feats(r.a, cd)
        if h is None or a is None: rows.append([np.nan] * 4); continue
        rows.append([(h.qb_epa + a.pass_def) + (a.qb_epa + h.pass_def), (h.rush_off + a.rush_def) + (a.rush_off + h.rush_def),
                     h.plays + a.plays, h.qb_change + a.qb_change])
    return pd.DataFrame(rows, columns=["pass_sum", "rush_sum", "pace", "qbchg_s"], index=D.index).assign(one=1.0)

# check: features as of the game's own date reproduce the player model's rows
chk = Gp.drop_duplicates(["date", "home", "away"]).merge(D[["gameday", "h", "a"]].rename(columns={"gameday": "date", "h": "home", "a": "away"}))
D["T_game"] = pd.to_datetime(D.gameday).dt.tz_localize(ET)
pg = player_inputs("T_game")
m = D[["gameday", "h", "a"]].join(pg).merge(chk[["date", "home", "away", "pass_sum", "pace"]], left_on=["gameday", "h", "a"],
                                            right_on=["date", "home", "away"], suffixes=("", "_ref"))
say(f"check: player features as of game day vs the player model's rows: n {len(m)}, max diff pass_sum "
    f"{(m.pass_sum - m.pass_sum_ref).abs().max():.2e}, pace {(m.pace - m.pace_ref).abs().max():.2e}")

# 4. lines and weather
S = pd.read_csv(os.path.join(W, "analysis", "nfl_timing_dk_snaps.csv.gz")); S["t"] = pd.to_datetime(S.t, utc=True).dt.tz_convert(ET)
idx = {kk: g.sort_values("t") for kk, g in S.groupby(["date", "h", "a"])}
def line_at(r, t, first=False):
    g = idx.get((r.gameday, r.h, r.a))
    if g is None or pd.isna(t): return np.nan
    if first: return float(g.point.iloc[0])
    g2 = g[g.t <= t]
    if not len(g2) or (t - g2.t.iloc[-1]) > pd.Timedelta(hours=24): return np.nan
    return float(g2.point.iloc[-1])
D["close"] = [float(idx[(r.gameday, r.h, r.a)].point.iloc[-1]) if (r.gameday, r.h, r.a) in idx else np.nan for r in D.itertuples()]
NB = pd.read_csv(os.path.join(N, "data", "external", "weather_forecasts", "nfl_iem_nbm_2022_2025.csv")).pivot_table(
    index="game_id", columns="days_before", values="wind_mph")
OM = pd.read_csv(os.path.join(N, "data", "external", "weather_forecasts", "nfl_forecasts_2022_2025.csv")).pivot_table(
    index="game_id", columns="days_before", values="temp_f")
def weather(T):
    lead = (D.kick - D[T]).dt.total_seconds() / 86400
    wind = np.full(len(D), np.nan); temp = np.full(len(D), np.nan); has = np.zeros(len(D), bool)
    for i, r in enumerate(D.itertuples()):
        L = lead.iloc[i]; n = None
        for c in (5, 6, 7):
            if abs(L - c) <= 0.5: n = c
        if L <= 1.5: n = 1
        if n is None or r.game_id not in NB.index: continue
        wind[i] = NB.loc[r.game_id, n]; tc = 6 if L >= 4.5 else 1
        temp[i] = OM.loc[r.game_id, tc] if (r.game_id in OM.index and tc in OM.columns) else np.nan; has[i] = True
    od = D.od.values
    w = np.where(od, np.where(np.isnan(wind), 0, wind), 0.0)
    c = np.where(od, np.clip(40 - np.where(np.isnan(temp), 60, temp), 0, None), 0.0)
    return w, c, has & od

# 5. v2 at each timing
V2 = {}
for T in ("T1", "T2", "T3"):
    X = player_inputs(T); line = np.array([line_at(r, getattr(r, T), first=(T == "T1")) for r in D.itertuples()])
    w, c, has = weather(T)
    nw = np.full(len(D), np.nan); fw = np.full(len(D), np.nan)
    for s in SEAS:
        m = (D.season == s).values
        team = D[f"team_{T}"].values[m]
        nw[m] = (team + X.loc[m, TF_N].values @ pcoef_n[s]) / 2
        Xw = X.loc[m].assign(wind_x=w[m], cold_x=c[m])
        fw[m] = (team + np.c_[w[m], c[m]] @ tcoef[s] + Xw[TF_W].values @ pcoef[s]) / 2
    V2[T] = dict(line=line, none=nw, fc=fw, has_fc=has, lead=((D.kick - D[T]).dt.total_seconds() / 86400).values)
    say(f"{T}: {np.isfinite(line).sum()} games with a line, median {np.nanmedian(V2[T]['lead']):.1f} days before kickoff, "
        f"forecast used for {int(has.sum())} outdoor games")

# 6. grading
def bets(pred, line):
    e = pred - line; b = (np.abs(e) >= 2) & np.isfinite(e)
    r = np.sign(e) * (D.tp.values - line)
    u = np.where(b, np.where(r > 0, 100 / 110, np.where(r < 0, -1.0, 0.0)), 0.0)
    clv = np.where(b, np.sign(e) * (D.close.values - line), np.nan)
    return b, r, u, clv, np.sign(e)
def combined(key):
    b = np.zeros(len(D), bool); u = np.zeros(len(D)); clv = np.full(len(D), np.nan); when = np.array([""] * len(D), dtype=object)
    r_all = np.full(len(D), np.nan)
    for T in ("T1", "T2", "T3"):
        bt, r, ut, ct, _ = bets(V2[T][key], V2[T]["line"]); new = bt & ~b
        u[new] = ut[new]; clv[new] = ct[new]; when[new] = T; r_all[new] = r[new]; b |= new
    return b, r_all, u, clv, when
wk = (D.season.astype(str) + "-" + D.week.astype(str)).values; uw = np.unique(wk); pos = {x: np.where(wk == x)[0] for x in uw}
rng = np.random.default_rng(20261104)
def boot(diff, mask):
    ws = [x for x in uw if mask[pos[x]].any()]; sums = np.array([diff[pos[x]][mask[pos[x]]].sum() for x in ws])
    B = rng.integers(0, len(ws), (10000, len(ws))); bs = sums[B].sum(1)
    return diff[mask].sum(), np.percentile(bs, 5), np.percentile(bs, 95)
def row(lab, b, r, u, clv, mask):
    bb = b & mask; w = int(((r > 0) & bb).sum()); l = int(((r < 0) & bb).sum())
    per = " ".join(f"{s % 100}:{u[mask & (D.season == s).values].sum():+.1f}" for s in sorted(D.season[mask].unique()))
    say(f"  {lab:40s} {w + l:4d} bets {w / max(w + l, 1):.1%} {u[mask].sum():+6.1f}u  ROI {u[mask].sum() / max(w + l, 1):+.1%}"
        f"  CLV {np.nanmean(clv[bb]) if bb.any() else np.nan:+.2f} pts   [{per}]")

ALL = D.season.between(2020, 2025).values; FC = D.season.between(2022, 2025).values
res = {}
for key, mask, lab in (("fc", FC, "FORECAST weather, 2022-25 (what live would do)"), ("none", ALL, "NO weather, 2020-25")):
    say(); say(lab)
    for T in ("T1", "T2", "T3"):
        b, r, u, clv, _ = bets(V2[T][key], V2[T]["line"]); res[(key, T)] = u
        row({"T1": "T1 lines first out (~11 d)", "T2": "T2 Monday 9 AM (~6 d)", "T3": "T3 Tuesday 11:45 AM (~5 d, live now)"}[T], b, r, u, clv, mask)
    b, r, u, clv, when = combined(key); res[(key, "comb")] = u
    row("combined: first of T1/T2/T3 with edge 2+", b, r, u, clv, mask)
    say("    combined bets placed at: " + ", ".join(f"{T} {int(((when == T) & mask).sum())}" for T in ("T1", "T2", "T3")))
    if key == "fc":
        pd.DataFrame(dict(game_id=D.game_id, season=D.season, week=D.week, when=when, units=u, clv=clv,
                          **{f"line_{T}": V2[T]["line"] for T in V2}, **{f"v2_{T}": V2[T]["fc"] for T in V2},
                          total=D.tp)).to_csv(os.path.join(W, "analysis", "nfl_timing_bets.csv"), index=False)

say(); say("Paired vs T3 (the current Tuesday lock), units difference, 90% interval resampling game weeks")
verdicts = {}
for alt in ("T1", "T2", "comb"):
    ef, lf, hf = boot(res[("fc", alt)] - res[("fc", "T3")], FC)
    en, ln, hn = boot(res[("none", alt)] - res[("none", "T3")], ALL)
    v = "BETTER" if (lf > 0 and en > 0) else ("consistent, not confirmed" if (ef > 0 and en > 0) else "not shown")
    verdicts[alt] = v
    say(f"  {alt:5s} forecast 2022-25: {ef:+6.1f}u [{lf:+.1f}, {hf:+.1f}]   no weather 2020-25: {en:+6.1f}u [{ln:+.1f}, {hn:+.1f}]   -> {v}")

# exploratory (labelled; not part of the decision): combined rule in time order when the opener was first seen after T2
say(); say("Exploratory (not pre-registered): opener first seen after Monday 9 AM in "
           f"{int((D.T1 > D.T2).sum())} of {len(D)} games; T3 vs T2 by game type")
thu = (D.kick.dt.dayofweek == 3).values
for key, mask in (("fc", FC), ("none", ALL)):
    for lab, mm in (("Thursday games", thu), ("other games", ~thu)):
        d = res[(key, "T2")] - res[(key, "T3")]
        say(f"  {key:4s} {lab:15s} T2 minus T3 {d[mask & mm].sum():+.1f}u")
open(os.path.join(W, "analysis", "nfl_timing_test_output.txt"), "w").write("\n".join(out) + "\n")
