"""Every game-day injury report as its own news event vs the DraftKings spread (rules: research/spreads/REPORT_SLOT_PREREG.md).
python3 analysis/report_slot_test.py   -> analysis/report_slot_test_output.txt, report_slot_events.csv.gz"""
import os, sys, glob, numpy as np, pandas as pd, statsmodels.api as sm
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); J = lambda *p: os.path.join(W, *p)
sys.path.insert(0, W)
from build_report_features import key, FULL2ABBR, ABBR2GAMES
out = []; say = lambda s="": (print(s), out.append(s))

# ---------------- player values
P = pd.read_csv(J("data", "external", "nba_box", "player_games_2012_2026.csv.gz"), dtype={"player_id": str}, parse_dates=["date"])
P = P[P.season >= 2021]; P["k"] = P.player.map(key); P["plus_minus"] = pd.to_numeric(P.plus_minus, errors="coerce").fillna(0)
pl = P[P.played == 1].sort_values("date")
ids = pl.groupby(["k", "season", "team"]).player_id.agg(lambda s: s.mode()[0]).to_dict()
ids_any = pl.groupby("k").player_id.agg(lambda s: s.mode()[0]).to_dict()
R = pd.read_csv(J("analysis", "rapm_by_season.csv"), dtype={"athlete_id": str})
rapm = {(int(r.season), r.athlete_id): r.rapm * r.minutes / (r.minutes + 1000) for r in R.itertuples()}
ps = pl.groupby(["season", "player_id"]).agg(pm=("plus_minus", "sum"), m=("minutes", "sum"))
pm48 = {(s, p): (r.pm / r.m * 48) * r.m / (r.m + 1000) if r.m > 0 else 0.0 for (s, p), r in ps.iterrows()}
last_mpg = pl.groupby(["season", "player_id"]).minutes.mean().to_dict()
hist = {k: (g.date.values, np.cumsum(g.minutes.values)) for k, g in pl.groupby(["season", "player_id"])}
def rating(pid, s): return rapm.get((s - 1, pid), pm48.get((s - 1, pid), 0.0))
def expmin(pid, d, s):
    h = hist.get((s, pid))
    if h is not None:
        n = np.searchsorted(h[0], np.datetime64(d), side="left")
        if n: return h[1][n - 1] / n
    return last_mpg.get((s - 1, pid), 0.0)
PM = pd.read_csv(J("data", "p_miss.csv"), index_col=0).iloc[:, 0].dropna().to_dict()

# ---------------- reports
rep = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(J("research", "injury_history", "reports_*.csv.gz")))], ignore_index=True)
rep["as_of"] = pd.to_datetime(rep.as_of, errors="coerce"); rep = rep.dropna(subset=["as_of", "team", "game_date"])
rep["gd"] = pd.to_datetime(rep.game_date, format="%m/%d/%Y", errors="coerce"); rep = rep.dropna(subset=["gd"])
rep["code"] = rep.team.map(FULL2ABBR).map(ABBR2GAMES); rep = rep.dropna(subset=["code"])
rep["k"] = rep.player.map(key)
rep["season"] = rep.gd.map(lambda d: d.year + 1 if d.month >= 8 else d.year)
nys = set(map(tuple, rep[rep.status == "NOT YET SUBMITTED"][["gd", "code", "as_of"]].values))
rp = rep[rep.player.notna()]
snaps = rep[["gd", "code", "as_of"]].drop_duplicates()
lists = {k: dict(zip(g.k, g.status)) for k, g in rp.groupby(["gd", "code", "as_of"])}
match = {"n": 0, "hit": 0}
def team_value(gd, code, as_of, season):
    v = 0.0
    for k_, st in lists.get((gd, code, as_of), {}).items():
        pmiss = PM.get(st, 0.0)
        if pmiss <= 0: continue
        pid = ids.get((k_, season, code), ids_any.get(k_)); match["n"] += 1
        if pid is None: continue
        match["hit"] += 1; v += pmiss * expmin(pid, gd, season) / 48 * rating(pid, season)
    return v

# ---------------- games, tips and DK lines
key3 = ["date", "home", "away"]
T = pd.read_csv(J("data", "training_games.csv"))[["season", "date", "home", "away", "home_pts", "away_pts"]]
S = pd.read_csv(J("data", "odds_history", "nba_snapshots.csv.gz"), usecols=["home", "away", "t", "tip", "book", "sp", "date"])
S = S[(S.book == "draftkings")].dropna(subset=["sp"]); S["t"] = pd.to_datetime(S.t, utc=True); S["tip"] = pd.to_datetime(S.tip, utc=True)
S = S[S.t < S.tip].sort_values("t"); S["L"] = -S.sp
lines = {k: g for k, g in S.groupby(key3)}
snaps_by = {k: g.as_of.sort_values().tolist() for k, g in snaps.groupby(["gd", "code"])}
ev = []
for g in T.itertuples():
    L = lines.get((g.date, g.home, g.away))
    if L is None or L.empty: continue
    gd = pd.Timestamp(g.date); tip_et = L.tip.iloc[0].tz_convert("America/New_York").tz_localize(None)
    seq = {}
    for side, code in (("h", g.home), ("a", g.away)):
        times = snaps_by.get((gd, code), [])
        start = [t for t in times if t.date() == (gd - pd.Timedelta(days=1)).date() and 20 <= t.hour <= 21 and (gd, code, t) not in nys]
        day = [t for t in times if t.date() == gd.date() and t <= tip_et - pd.Timedelta(minutes=30) and (gd, code, t) not in nys]
        if not day: continue
        prev = team_value(gd, code, start[-1], g.season) if start else team_value(gd, code, day[0], g.season)
        day = day if start else day[1:]
        for t in day:
            v = team_value(gd, code, t, g.season); dv = v - prev; prev = v
            if abs(dv) >= 0.5: seq.setdefault(t, 0.0); seq[t] += (-dv if side == "h" else dv)
    for t0, N in sorted(seq.items()):
        t0u = pd.Timestamp(t0).tz_localize("America/New_York").tz_convert("UTC")
        pre = L[L.t <= t0u]; act = L[L.t >= t0u + pd.Timedelta(minutes=15)]
        if pre.empty or act.empty: continue
        ev.append(dict(season=g.season, date=g.date, home=g.home, away=g.away, t0=t0, N=N, hour=t0.hour,
                       L_open=L.L.iloc[0], L_pre=pre.L.iloc[-1], L_act=act.L.iloc[0], act_lag=(act.t.iloc[0] - t0u).total_seconds() / 60,
                       L_close=L.L.iloc[-1], margin=g.home_pts - g.away_pts))
E = pd.DataFrame(ev)
say("# Every game-day injury report vs DraftKings spread (results)"); say()
say(f"player name match rate {match['hit']/max(1,match['n']):.1%}; events (|news| >= 0.5) {len(E)} {E.groupby('season').size().to_dict()}")
say(f"minutes from report to the act line: median {E.act_lag.median():.0f}, 10th-90th {E.act_lag.quantile(.1):.0f}-{E.act_lag.quantile(.9):.0f}; "
    f"report hour counts {E.hour.value_counts().sort_index().to_dict()}"); say()
B = E.season.isin([2022, 2023])
E["after"] = E.L_close - E.L_act; E["moved"] = E.L_act - E.L_pre
X = sm.add_constant(E.loc[B, ["N", "moved"]]); m = sm.OLS(E.loc[B, "after"], X).fit()
say(f"build fit: move after act = {m.params['const']:+.3f} + {m.params['N']:+.3f} x N (se {m.bse['N']:.3f}) + {m.params['moved']:+.3f} x moved (se {m.bse['moved']:.3f})")
mf = sm.OLS((E.L_close - E.L_pre)[B], sm.add_constant(E.loc[B, "N"])).fit()
say(f"build: move from just before the report to the close per point of news {mf.params['N']:+.3f} (se {mf.bse['N']:.3f})")
E["R"] = m.params["N"] * E.N + m.params["moved"] * E.moved
win = (E.margin > E.L_act).astype(float); push = E.margin == E.L_act
lg = sm.Logit(win[B & ~push], sm.add_constant((E.L_close - E.L_act)[B & ~push])).fit(disp=0)
be = (np.log(0.5238 / 0.4762) - lg.params.iloc[0]) / lg.params.iloc[1]; say(f"break-even CLV at the act line (build): {be:+.2f} pts"); say()

def bets(mask, th):
    g = E[mask & (E.R.abs() >= th)].sort_values("t0").drop_duplicates(["date", "home"]); side = np.sign(g.R)
    clv = side * (g.L_close - g.L_act); res = side * (g.margin - g.L_act)
    return pd.DataFrame(dict(season=g.season, clv=clv, u=np.where(res > 0, 100 / 110, np.where(res < 0, -1.0, 0.0)), w=res > 0, p=res == 0))
def row(D, lab):
    if D.empty: return f"| {lab} | 0 | | | | |"
    per = D.groupby("season").agg(u=("u", "sum"), c=("clv", "mean"), n=("u", "size"))
    return (f"| {lab} | {len(D)} | {D.clv.mean():+.2f} | {D.u.sum():+.1f}u ({D.u.mean()*100:+.1f}%) | {D.w.sum()/max(1,(~D.p).sum())*100:.1f}% | "
            + " ".join(f"{s%100:02d}: {r.n} bets {r.u:+.1f}u CLV {r.c:+.2f}" for s, r in per.iterrows()) + " |")
say("| Set | Bets | CLV | Units | Win % | By season |"); say("|---|---|---|---|---|---|")
cand = []
for th in (0.5, 0.75, 1.0):
    D = bets(B, th); say(row(D, f"build, theta {th}"))
    if len(D) >= 50: cand.append((D.clv.mean(), th))
TH = max(cand)[1] if cand else 0.5
D = bets(~B, TH); say(row(D, f"**TEST 2023-26, theta {TH} (chosen on build)**"))
pos = (D.groupby("season").clv.mean() > 0).sum() if len(D) else 0
cm = D.clv.mean() if len(D) else np.nan
verdict = "PASS" if (len(D) and cm >= be and D.u.sum() > 0 and pos >= 2) else ("PARTIAL" if len(D) and cm > 0 else "FAIL")
say(f"verdict: **{verdict}** (CLV {cm:+.2f} vs break-even {be:+.2f}; units {D.u.sum() if len(D) else 0:+.1f}; CLV positive in {pos} of 3 seasons)"); say()

say("Absorption by window, |N| >= 1.0: line move per point of news in each window, and its share of the open-to-close move (all seasons; descriptive)")
big = E[E.N.abs() >= 1.0].copy()
big["by_hour"] = pd.cut(big.hour, [0, 12, 15, 18, 24], labels=["before noon", "noon-3 PM", "3-6 PM", "after 6 PM"], right=False)
def slope(y, x): return float(np.sum(x * y) / np.sum(x * x))
for lab, g in [("all", big)] + list(big.groupby("by_hour", observed=True)):
    tot = slope(g.L_close - g.L_open, g.N)
    w = [slope(g.L_pre - g.L_open, g.N), slope(g.L_act - g.L_pre, g.N), slope(g.L_close - g.L_act, g.N)]
    say(f"  {lab:>12} (n {len(g)}): open->report {w[0]:+.2f} ({w[0]/tot:.0%}), report->act {w[1]:+.2f} ({w[1]/tot:.0%}), "
        f"act->close {w[2]:+.2f} ({w[2]/tot:.0%}); open->close {tot:+.2f} per pt")
E.to_csv(J("analysis", "report_slot_events.csv.gz"), index=False)
open(J("analysis", "report_slot_test_output.txt"), "w").write("\n".join(out) + "\n")
