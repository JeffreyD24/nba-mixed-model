"""Out-of-sample test of the NFL wind-under rule, 2011-21 (pre-registered: nfl-mixed-model data/external/weather_forecasts/WIND_OOS_PREREG.md,
pushed in commit 922a7a9 before any 2011-21 forecast was fetched).
Primary: UNDER at the SBR closing total (-110) when the 1-day GFS-MAV wind forecast >= 12.7 mph; holdout 2018-21; verdict from ROI and
the 90% bootstrap range resampling game days. Secondary: 2011-17, MAV >= 12.0, NBS >= 12.0, nflverse total_line.
  python analysis/nfl_wind_oos_test.py NFL_REPO  -> analysis/nfl_wind_oos_test_output.txt"""
import os, sys
import numpy as np, pandas as pd
N = os.path.abspath(sys.argv[1])
here = os.path.dirname(os.path.abspath(__file__))
out = []
def say(*a):
    out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
rng = np.random.default_rng(20261103)
WIN, LOSS = 100 / 110, -1.0

G = pd.read_csv(os.path.join(N, "data", "nflverse_games.csv"))
G = G[(G.game_type == "REG") & G.season.between(2011, 2021) & G.roof.isin(["outdoors", "open"]) & (G.location == "Home")].copy()
G["pts"] = G.home_score + G.away_score
G["wind_rec"] = pd.to_numeric(G.wind, errors="coerce")

F = pd.read_csv(os.path.join(N, "data", "external", "weather_forecasts", "nfl_iem_hist_2011_2021.csv"))
wide = F.pivot_table(index="game_id", columns="model", values="wind_mph").reset_index()
wide = wide.rename(columns={"GFS": "mav", "NBS": "nbs"})
for c in ("mav", "nbs"):
    if c not in wide: wide[c] = np.nan

S = pd.read_csv(os.path.join(N, "data", "external", "sbr", "sbr_nfl_2011_2021_clean.csv.gz"))
S = S[S.total_trusted == 1][["date", "home_final", "away_final", "close_over_under", "home_team", "away_team"]]
# join on date + both final scores (SBR team names are ambiguous for NY / LA); drop any key that is not unique on either side
key = ["gameday", "home_score", "away_score"]
S = S.rename(columns={"date": "gameday", "home_final": "home_score", "away_final": "away_score", "home_team": "sbr_home", "away_team": "sbr_away"})
S = S[~S.duplicated(key, keep=False)]
D = G.merge(wide, on="game_id", how="left").merge(S, on=key, how="left")
say(f"outdoor home-site regular-season games 2011-21: {len(G)}; with MAV 1-d forecast {D.mav.notna().sum()}, with NBS {D.nbs.notna().sum()}, "
    f"with SBR closing total {D.close_over_under.notna().sum()}")
say("by season (games, MAV, NBS, SBR close): " + str({s: (len(x), int(x.mav.notna().sum()), int(x.nbs.notna().sum()), int(x.close_over_under.notna().sum()))
                                                       for s, x in D.groupby("season")}))
# sanity: SBR close vs nflverse total_line
both = D.dropna(subset=["close_over_under", "total_line"])
say(f"SBR close vs nflverse total_line: n={len(both)}, mean abs diff {(both.close_over_under - both.total_line).abs().mean():.2f}, "
    f"exact {(both.close_over_under == both.total_line).mean():.1%}")
say(f"MAV 1-d vs recorded game wind: r={D[['mav', 'wind_rec']].dropna().corr().iloc[0, 1]:.2f} (n={len(D[['mav', 'wind_rec']].dropna())}); "
    f"mean MAV {D.mav.mean():.1f}, share >= 12.7: {(D.mav >= 12.7).mean():.1%}")
say("")

def grade(X, line, fc, thr):
    X = X.dropna(subset=[line, fc]); X = X[X[fc] >= thr].copy()
    X["res"] = np.sign(X[line] - X.pts)            # +1 under wins, -1 loses, 0 push
    X = X[X.res != 0]
    X["u"] = np.where(X.res > 0, WIN, LOSS)
    return X

def boot_days(X, B=10000):
    if len(X) < 2: return (np.nan, np.nan)
    days = X.groupby("gameday").u.agg(["sum", "count"]).values
    idx = rng.integers(0, len(days), size=(B, len(days)))
    s = days[idx, 0].sum(1); c = days[idx, 1].sum(1)
    r = s / c
    return np.percentile(r, 5), np.percentile(r, 95)

def line_txt(X, label):
    if not len(X): return f"  {label}: 0 bets"
    lo, hi = boot_days(X)
    roi = X.u.mean()
    bys = " ".join(f"{str(s)[2:]}:{x.u.sum():+.1f}" for s, x in X.groupby("season"))
    return (f"  {label}: {len(X):4d} bets {np.mean(X.u > 0):.1%} {X.u.sum():+6.1f}u ROI {roi:+.1%} [90% {lo:+.1%}, {hi:+.1%}]  by season {bys}"), roi, lo

H = D[D.season.between(2018, 2021)]; E = D[D.season.between(2011, 2017)]
say("1. PRIMARY (pre-registered): UNDER at SBR closing total, -110, 1-day MAV wind >= 12.7 mph, 2018-21")
t, roi, lo = line_txt(grade(H, "close_over_under", "mav", 12.7), "2018-21")
say(t)
verdict = "CONFIRMED" if roi > 0 and lo > 0 else ("CONSISTENT, NOT CONFIRMED" if roi > 0 else "NOT CONFIRMED")
say(f"  VERDICT (pre-registered rule): {verdict}")
say("")
say("2. Secondary (reported, no verdict weight)")
for lab, X, ln, fc, thr in [("2011-17, MAV >= 12.7, SBR close", E, "close_over_under", "mav", 12.7),
                            ("2011-21, MAV >= 12.7, SBR close", D, "close_over_under", "mav", 12.7),
                            ("2018-21, MAV >= 12.0, SBR close", H, "close_over_under", "mav", 12.0),
                            ("2011-17, MAV >= 12.0, SBR close", E, "close_over_under", "mav", 12.0),
                            ("2018-21, NBS >= 12.0, SBR close", H, "close_over_under", "nbs", 12.0),
                            ("2018-21, MAV >= 12.7, nflverse total_line", H, "total_line", "mav", 12.7),
                            ("2011-17, MAV >= 12.7, nflverse total_line", E, "total_line", "mav", 12.7)]:
    r = line_txt(grade(X, ln, fc, thr), lab); say(r if isinstance(r, str) else r[0])
say("")
say("3. Slope of (final total - SBR closing total) on 1-day MAV wind, points per mph (OLS; t from game-day cluster bootstrap)")
def slope(X):
    X = X.dropna(subset=["mav", "close_over_under"]); y = X.pts - X.close_over_under; x = X.mav
    b = np.polyfit(x, y, 1)[0]
    days = X.gameday.unique(); bs = []
    grp = {d: i for d, i in X.groupby("gameday").groups.items()}
    for _ in range(2000):
        pick = rng.choice(days, len(days)); ii = np.concatenate([grp[d] for d in pick])
        bs.append(np.polyfit(x.loc[ii], y.loc[ii], 1)[0])
    return b, b / np.std(bs), len(X)
for lab, X in [("2018-21", H), ("2011-17", E), ("2011-21", D)] + [(str(s), x) for s, x in D.groupby("season")]:
    b, t, n = slope(X); say(f"  {lab}: {b:+.3f} (t {t:+.1f}) n={n}")
say("  (2022-25 in-sample, NBM, close: 1 d -0.368, t -3.4)")
say("")
say("4. Bins of 1-day MAV wind, 2011-21: mean (total - SBR close), under rate (pushes dropped)")
X = D.dropna(subset=["mav", "close_over_under"]).copy()
X["bin"] = pd.cut(X.mav, [0, 8, 12.7, 16, 99], labels=["<8", "8-12.7", "12.7-16", "16+"], right=False)
for b, Y in X.groupby("bin", observed=True):
    Z = Y[Y.pts != Y.close_over_under]
    say(f"  {b:>8}: n={len(Y):4d} total-close {(Y.pts - Y.close_over_under).mean():+.2f}  under {np.mean(Z.pts < Z.close_over_under):.1%}")
open(os.path.join(here, "nfl_wind_oos_test_output.txt"), "w").write("\n".join(out) + "\n")
