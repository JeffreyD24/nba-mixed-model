"""Leakage check (Nov 3, 2026): does Model 1's opening-line record depend on results the opener could not have known?
NBA openers post ~8:30 PM ET the night before, while that night's games are being played, and the live tracker locks tomorrow's
model in the morning. The backtests' walk-forward used every game before the game date (date < d), i.e. it also knew the night
before. This reruns Model 1 at DraftKings' openers (2023-24 .. 2025-26) both ways:
  lag 0 = as backtested so far (results through the night before)
  lag 1 = results through two nights before (what the live morning lock knows)
Same seasons, same training, same injury snapshot (night-before report). Model 1 only: no luck correction or form.
  python analysis/lag_leak_test.py WORKDIR   -> analysis/lag_leak_test_output.txt"""
import os, sys, io, contextlib
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
import nba_mixed_model as nm

src = open(os.path.join(W, "nba_mixed_model.py")).read()
assert "past = L_all[L_all.date < d]" in src
lagged = src.replace("past = L_all[L_all.date < d]", "past = L_all[L_all.date < d - pd.Timedelta(days=LAG_DAYS)]")
ns = {"__name__": "nm_lag"}; exec(compile(lagged, "nba_mixed_model_lag", "exec"), ns)

T = pd.read_csv(os.path.join(W, "data", "training_games.csv"))
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nba_open_close.csv"))
dk = O[O.book == "draftkings"][["date", "home", "away", "open_spread", "open_total"]]
T = T.drop(columns=["open_spread", "open_total"]).merge(dk, on=["date", "home", "away"], how="left")

out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
def grade(e, r):
    m = e.abs() >= 3; rr = np.sign(e[m]) * r[m]; w, l = int((rr > 0).sum()), int((rr < 0).sum())
    return w + l, w / max(w + l, 1), w * 100 / 110 - l

res = {}
for lag in (0, 1):
    ns["LAG_DAYS"] = lag
    for test in (2024, 2025, 2026):
        train = [s for s in range(2022, test)]
        with contextlib.redirect_stdout(io.StringIO()):
            s, P = ns["run"](T[T.season.isin(train + [test])], train, test, today_suffix="_open")
        P = P.dropna(subset=["open_spread", "open_total"])
        res[(lag, test)] = P
say("Model 1 at DraftKings openers, edge 3+, night-before injury report. lag 0 = knows the night before; lag 1 = live morning lock.")
for mk in ("spread", "total"):
    say(f"\n{mk.upper()}")
    for lag in (0, 1):
        row, tot = [], [0, 0, 0.0]
        for test in (2024, 2025, 2026):
            P = res[(lag, test)]
            if mk == "spread": e, r = P.pred_margin + P.open_spread, (P.home_pts - P.away_pts) + P.open_spread
            else: e, r = P.pred_total - P.open_total, (P.home_pts + P.away_pts) - P.open_total
            n, wp, u = grade(e, r); row.append(f"{test}: {n} {wp:.1%} {u:+.1f}u")
            tot[0] += n; tot[1] += wp * n; tot[2] += u
        say(f"  lag {lag}: " + " | ".join(row) + f" | all: {tot[0]} {tot[1] / tot[0]:.1%} {tot[2]:+.1f}u")
for lag in (0, 1):
    mae = []
    for test in (2024, 2025, 2026):
        P = res[(lag, test)]
        mae.append(f"{test} margin MAE {np.abs(P.pred_margin - (P.home_pts - P.away_pts)).mean():.2f}, total MAE {np.abs(P.pred_total - (P.home_pts + P.away_pts)).mean():.2f}")
    say(f"lag {lag}: " + "; ".join(mae))
open(os.path.join(W, "analysis", "lag_leak_test_output.txt"), "w").write("\n".join(out) + "\n")

# ---------------------------------------------------------------- live totals add-ons (luck correction + last-10 form)
# Both were built from every earlier game, including the night before. Recompute each with a cutoff before the game date
# (lag 0) and before the previous night (lag 1), then grade the live totals number (Model 1 + luck 0.5 + form 0.20)
# at the opener, both teams 10+ games, exactly as analysis/form_adjust.py does (without the v4 altitude/shrink terms).
TG = pd.read_csv(os.path.join(W, "analysis", "shot_quality_team_games.csv.gz"))
TG["date"] = pd.to_datetime(TG.date)
TT = T.copy(); TT["date"] = pd.to_datetime(TT.date)
pts = pd.concat([TT[["season", "date", "home"]].rename(columns={"home": "team"}).assign(tp=TT.home_pts + TT.away_pts),
                 TT[["season", "date", "away"]].rename(columns={"away": "team"}).assign(tp=TT.home_pts + TT.away_pts)])
TG = TG.merge(pts, on=["season", "date", "team"], how="left")
hist = {k: g.sort_values("date") for k, g in TG.groupby(["season", "team"])}

def feats(season, team, d, lag):
    g = hist.get((season, team))
    if g is None: return (np.nan,) * 4
    g = g[g.date < d - pd.Timedelta(days=lag)]
    n = len(g)
    if n < 5: return (n, np.nan, np.nan, np.nan)
    luck = g.luck.mean() + g.opp_luck.mean()
    f10 = g.tp.tail(10).mean() - g.tp.mean() if n >= 6 else np.nan
    return (n, luck, f10, np.nan)

for lag in (0, 1):
    rows = []
    for test in (2024, 2025, 2026):
        P = res[(lag, test)].copy(); P["date"] = pd.to_datetime(P.date)
        for side in ("home", "away"):
            F = [feats(test, t, d, lag) for t, d in zip(P[side], P.date)]
            P[f"{side}_n"] = [f[0] for f in F]; P[f"{side}_luck"] = [f[1] for f in F]; P[f"{side}_f10"] = [f[2] for f in F]
        P["L"] = P.home_luck + P.away_luck
        lg = P.groupby("date").L.transform("mean")
        P["pt_live"] = P.pred_total + np.where((P.home_n >= 5) & (P.away_n >= 5), (-0.5 * (P.L - lg)).fillna(0), 0)
        P["tot_model"] = P.pt_live + 0.20 * (P.home_f10 + P.away_f10).fillna(0)
        P = P[(P.home_n >= 10) & (P.away_n >= 10)]
        rows.append(P.assign(season=test))
    R = pd.concat(rows); res[("live", lag)] = R
say("\nLIVE TOTALS NUMBER (Model 1 + luck correction + last-10 form), opener, edge 3+, both teams 10+ games")
for lag in (0, 1):
    R = res[("live", lag)]; row, tot = [], [0, 0, 0.0]
    for test in (2024, 2025, 2026):
        P = R[R.season == test]; n, wp, u = grade(P.tot_model - P.open_total, (P.home_pts + P.away_pts) - P.open_total)
        row.append(f"{test}: {n} {wp:.1%} {u:+.1f}u"); tot[0] += n; tot[1] += wp * n; tot[2] += u
    say(f"  lag {lag}: " + " | ".join(row) + f" | all: {tot[0]} {tot[1] / tot[0]:.1%} {tot[2]:+.1f}u")
open(os.path.join(W, "analysis", "lag_leak_test_output.txt"), "w").write("\n".join(out) + "\n")
