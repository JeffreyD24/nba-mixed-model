"""NHL: does Pinnacle (the sharp book) open before DraftKings, does DraftKings follow it, and does Pinnacle's price help
the shot model? Moneyline, no-vig home win chance. Uses data/odds_history/nhl_snapshots.csv.gz and nhl-mixed-model's
_tmp/dk_holdout_{2022,2023,2024}.csv (shot model predictions).
  python analysis/sharp_nhl.py WORKDIR NHL_REPO"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); N = os.path.abspath(sys.argv[2])
dec = lambda o: np.where(o > 0, 1 + o / 100, 1 + 100 / np.abs(o))
O = pd.read_csv(os.path.join(W, "data", "odds_history", "nhl_snapshots.csv.gz"), parse_dates=["t", "tip"]).dropna(subset=["ml_h", "ml_a"])
ih, ia = 1 / dec(O.ml_h), 1 / dec(O.ml_a); O["p"] = ih / (ih + ia)
P = pd.concat([pd.read_csv(os.path.join(N, "_tmp", f"dk_holdout_{s}.csv")) for s in (2022, 2023, 2024)])
P = P[["date", "home", "away", "season", "home_goals", "away_goals", "p_home_win_open", "open_home_ml", "open_away_ml", "t0"]].rename(columns={"t0": "open_t"})
X = O[O.book.isin(["draftkings", "pinnacle"])].pivot_table(index=["date", "home", "away", "t"], columns="book", values="p").reset_index()
f = O[O.book.isin(["draftkings", "pinnacle"])].groupby(["date", "home", "away", "book"]).t.min().unstack()
print(f"Pinnacle posts its moneyline before DraftKings in {(f.pinnacle < f.draftkings).mean():.0%} of games; median gap DK-Pinnacle "
      f"{((f.draftkings - f.pinnacle).dt.total_seconds() / 3600).median():.1f} h")
# B: DK vs Pinnacle disagreement at the same snapshot -> bet DK on the side Pinnacle likes more (first time per game)
X = X.merge(P[["date", "home", "away", "home_goals", "away_goals", "season"]], on=["date", "home", "away"]).dropna(subset=["draftkings", "pinnacle"])
S = O[O.book == "draftkings"][["date", "home", "away", "t", "ml_h", "ml_a"]]
X = X.merge(S, on=["date", "home", "away", "t"], how="left")
X["gap"] = X.pinnacle - X.draftkings; hw = X.home_goals > X.away_goals
print("\nBet DraftKings' moneyline when Pinnacle's no-vig win chance is k points higher for that side (first time per game):")
for k in (0.01, 0.02, 0.03, 0.04):
    s = X[X.gap.abs() >= k].sort_values("t").groupby(["date", "home", "away"]).head(1)
    home = s.gap > 0; d = np.where(home, dec(s.ml_h), dec(s.ml_a)); win = np.where(home, s.home_goals > s.away_goals, s.away_goals > s.home_goals)
    u = np.where(win, d - 1, -1)
    print(f"  {k:.0%}+: {len(s)} bets, won {win.mean():.1%}, {u.sum():+.1f}u ({u.sum() / len(s):+.1%}); by season " +
          ", ".join(f"{yr}: {u[s.season.values == yr].sum():+.1f}" for yr in (2022, 2023, 2024)))
# C: shot model bets at the DK opener, split by where Pinnacle is at that moment (or its opener if it isn't up yet)
P["open_t"] = pd.to_datetime(P.open_t, utc=True)
pin = O[O.book == "pinnacle"][["date", "home", "away", "t", "p"]].merge(P[["date", "home", "away", "open_t"]], on=["date", "home", "away"])
pa = pin[pin.t <= pin.open_t].sort_values("t").groupby(["date", "home", "away"]).tail(1).rename(columns={"p": "pin_p_at"})
pf = pin.sort_values("t").groupby(["date", "home", "away"]).head(1).rename(columns={"p": "pin_p_first", "t": "pin_t"})
pc = pin.sort_values("t").groupby(["date", "home", "away"]).tail(1).rename(columns={"p": "pin_p_close"})
P = P.merge(pa[["date", "home", "away", "pin_p_at"]], on=["date", "home", "away"], how="left").merge(pf[["date", "home", "away", "pin_p_first", "pin_t"]], on=["date", "home", "away"], how="left").merge(pc[["date", "home", "away", "pin_p_close"]], on=["date", "home", "away"], how="left")
dh, da = dec(P.open_home_ml), dec(P.open_away_ml); ih, ia = 1 / dh, 1 / da; P["dk_p"] = ih / (ih + ia)
evh, eva = P.p_home_win_open * dh - 1, (1 - P.p_home_win_open) * da - 1
home = evh >= eva; ev = np.maximum(evh, eva); win = np.where(home, P.home_goals > P.away_goals, P.away_goals > P.home_goals)
u = np.where(win, np.where(home, dh, da) - 1, -1)
m = ev >= 0.06
print(f"\nShot model moneyline bets at DK's opener, EV 6%+: {m.sum()} bets, {u[m].sum():+.1f}u")
print(f"  Pinnacle already up at DK's open: {P.pin_p_at.notna().mean():.0%} of games")
for lab, pp in (("Pinnacle at DK's open", P.pin_p_at), ("Pinnacle's first price", P.pin_p_first), ("Pinnacle's close (hindsight)", P.pin_p_close)):
    diff = np.where(home, pp - P.dk_p, P.dk_p - pp)     # + = Pinnacle likes our side more than DK
    for lab2, k in (("agrees (likes our side more)", diff > 0.005), ("about the same", np.abs(diff) <= 0.005), ("disagrees", diff < -0.005)):
        s = m & k & pp.notna()
        print(f"  {lab:28s} {lab2:30s}: {s.sum():4d} bets, {u[s].sum():+6.1f}u ({u[s].sum() / max(s.sum(), 1):+.1%})")
# D: the practical version: wait for Pinnacle's first price, then bet at DraftKings' price AT THAT MOMENT
dkS = O[O.book == "draftkings"][["date", "home", "away", "t", "ml_h", "ml_a", "p"]].merge(P[["date", "home", "away", "pin_t"]], on=["date", "home", "away"])
dkS = dkS[dkS.t <= dkS.pin_t].sort_values("t").groupby(["date", "home", "away"]).tail(1).rename(columns={"ml_h": "w_h", "ml_a": "w_a", "p": "dk_p_w"})
Q = P.merge(dkS[["date", "home", "away", "w_h", "w_a", "dk_p_w"]], on=["date", "home", "away"], how="left")
dh, da = dec(Q.w_h), dec(Q.w_a)
evh, eva = Q.p_home_win_open * dh - 1, (1 - Q.p_home_win_open) * da - 1
home = evh >= eva; ev = np.maximum(evh, eva); win = np.where(home, Q.home_goals > Q.away_goals, Q.away_goals > Q.home_goals)
u = np.where(win, np.where(home, dh, da) - 1, -1)
diff = np.where(home, Q.pin_p_first - Q.dk_p_w, Q.dk_p_w - Q.pin_p_first)
print("\nWait for Pinnacle, then bet DraftKings' price at that moment (shot model EV 6%+):")
for lab, k in (("all", np.ones(len(Q), bool)), ("Pinnacle agrees or same", diff >= -0.005), ("Pinnacle disagrees", diff < -0.005)):
    s = (ev >= 0.06) & k & Q.w_h.notna()
    print(f"  {lab:26s}: {s.sum():4d} bets, {u[s].sum():+6.1f}u ({u[s].sum() / max(s.sum(), 1):+.1%}); by season " +
          ", ".join(f"{yr}: {u[s & (Q.season.values == yr)].sum():+.1f}" for yr in (2022, 2023, 2024)))
# E: bet at DK's opener as now, but only keep bets Pinnacle's first price doesn't disagree with (needs both prices)
evh0, eva0 = P.p_home_win_open * dec(P.open_home_ml) - 1, (1 - P.p_home_win_open) * dec(P.open_away_ml) - 1
home0 = evh0 >= eva0; d0 = np.where(home0, P.pin_p_first - P.dk_p, P.dk_p - P.pin_p_first)
win0 = np.where(home0, P.home_goals > P.away_goals, P.away_goals > P.home_goals); u0 = np.where(win0, np.where(home0, dec(P.open_home_ml), dec(P.open_away_ml)) - 1, -1)
for yr in (2022, 2023, 2024):
    s = (np.maximum(evh0, eva0) >= 0.06) & (P.season.values == yr)
    print(f"  {yr} at DK open: all {s.sum()} bets {u0[s].sum():+.1f}u | Pinnacle first price disagrees: {(s & (d0 < -0.005)).sum()} bets {u0[s & (d0 < -0.005)].sum():+.1f}u")
# F: of the bets at DK's opener, how many still had value at DK's price when Pinnacle posted?
s0 = np.maximum(evh0, eva0) >= 0.06
same_side = home0 == home
still = s0 & (ev >= 0.06) & same_side & Q.w_h.notna()
gone = s0 & ~still & Q.w_h.notna()
hrs = ((P.pin_t - P.open_t).dt.total_seconds() / 3600)
print(f"\nOf {s0.sum()} bets at DK's opener: Pinnacle posted {hrs[s0].median():.1f} h later (median). Still 6%+ value at DK then: "
      f"{still.sum()} ({still.sum() / s0.sum():.0%}); those made {u[still].sum():+.1f}u waiting vs {u0[still].sum():+.1f}u at the open. "
      f"Value gone: {gone.sum()} bets, which made {u0[gone].sum():+.1f}u at the open")
for lab, k in (("still value AND Pinnacle agrees/same", still & (diff >= -0.005)), ("still value, Pinnacle disagrees", still & (diff < -0.005))):
    print(f"  {lab}: {k.sum()} bets, {u[k].sum():+.1f}u waiting")
