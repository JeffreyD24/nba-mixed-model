"""NBA spreads: the "recent arrival" Feb-Apr trap on 2013-14..2021-22 at SBR openers (Nov 6, 2026).

Pre-registered: betting-goals/models/tests/NBA_ARRIVAL_TRAP_SBR_PREREG.md (pushed e80e3cc before computing).
Bets and standings from analysis/spread_filters_sbr_bets.csv (run analysis/spread_filters_sbr.py first). Arrivals as tracker.py
(lines 314-321) from Kaggle eoinamoore box scores (data/external/kaggle/eoinamoore/PlayerStatistics_*.csv.gz), games before the date only.
Live filter as alert.py (862-873): home underdogs excluded in every month; Feb-Apr also no bets on tanking teams or against 5-10 teams.
  python analysis/arrival_trap_sbr.py .  -> analysis/arrival_trap_sbr_output.txt, analysis/arrival_trap_sbr_bets.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
BOOT, SEED = 10000, 20261106
CODE = {"Hawks": "atl", "Celtics": "bos", "Nets": "bkn", "Bobcats": "cha", "Bulls": "chi", "Cavaliers": "cle", "Mavericks": "dal",
        "Nuggets": "den", "Pistons": "det", "Warriors": "gs", "Rockets": "hou", "Pacers": "ind", "Clippers": "lac", "Lakers": "lal",
        "Grizzlies": "mem", "Heat": "mia", "Bucks": "mil", "Timberwolves": "min", "Pelicans": "no", "Knicks": "ny", "Thunder": "okc",
        "Magic": "orl", "76ers": "phi", "Suns": "phx", "Trail Blazers": "por", "Kings": "sac", "Spurs": "sa", "Raptors": "tor",
        "Jazz": "utah", "Wizards": "wsh"}
out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)

# ---- player games (regular season, played)
parts = []
for y in range(2012, 2022):
    p = pd.read_csv(os.path.join(W, "data", "external", "kaggle", "eoinamoore", f"PlayerStatistics_{y}_{str(y + 1)[2:]}.csv.gz"),
                    usecols=["personId", "gameDateTimeEst", "playerteamCity", "playerteamName", "gameType", "numMinutes"], low_memory=False)
    p = p[p.gameType.astype(str).str.contains("Regular") & (p.numMinutes > 0)].copy()
    p["team"] = np.where(p.playerteamName == "Hornets", np.where(p.playerteamCity == "New Orleans", "no", "cha"), p.playerteamName.map(CODE))
    p["season"] = y + 1
    parts.append(p)
PG = pd.concat(parts, ignore_index=True)
assert PG.team.notna().all(), PG[PG.team.isna()][["playerteamCity", "playerteamName"]].drop_duplicates()
PG["d"] = pd.to_datetime(PG.gameDateTimeEst.astype(str).str[:10])
first_season = PG.groupby(["season", "personId"]).d.min().rename("fs")
st = PG.groupby(["season", "personId", "team"]).d.min().rename("t0").reset_index().join(first_season, on=["season", "personId"])
st = st[st.t0 > st.fs + pd.Timedelta(days=3)]                       # joined from another team (or first appeared 4+ days in)
PGk = PG.merge(st[["season", "personId", "team", "t0"]], on=["season", "personId", "team"])
by = {k: g.sort_values("d") for k, g in PGk.groupby(["season", "team"])}
def arrivals(season, team, d):
    g = by.get((season, team))
    if g is None: return 0
    g = g[(g.d < d) & (g.t0 >= d - pd.Timedelta(days=30))]
    if not len(g): return 0
    a = g.groupby("personId").numMinutes.agg(["size", "mean"])
    return int(((a["size"] >= 3) & (a["mean"] >= 12)).sum())

B = pd.read_csv(os.path.join(W, "analysis", "spread_filters_sbr_bets.csv"))
B["d"] = pd.to_datetime(B.date)
hb = B.side == "home"
B["our_team"] = np.where(hb, B.home, B.away); B["opp_team"] = np.where(hb, B.away, B.home)
B["our_arr"] = [arrivals(s, t, d) for s, t, d in zip(B.season, B.our_team, B.d)]
B["opp_arr"] = [arrivals(s, t, d) for s, t, d in zip(B.season, B.opp_team, B.d)]
B["late"] = B.late.astype(bool); B["home_dog"] = B.home_dog.astype(bool)
pre = ~B.home_dog & ~(B.late & ((B.our == "tanking") | (B.opp == "middle")))   # live filter except the arrival trap
SEAS = sorted(B.season.unique())

say("NBA arrival trap at SBR openers 2013-14..2021-22 (Model 1 no injuries, edge 3+, -110, trusted, both teams 10+ games)")
say(f"player-games {len(PG)}; mid-season joins {len(st)}; bets {len(B)}; late bets with our arrival>0: {(B.late & (B.our_arr > 0)).sum()}")
say("late bets with an arrival, by season: " + " ".join(f"{s % 100}:{int((B.late & (B.our_arr > 0) & (B.season == s)).sum())}" for s in SEAS))
def row(G, lab):
    w, l = int((G.result > 0).sum()), int((G.result < 0).sum())
    bys = " ".join(f"{s % 100}:{G[G.season == s].units.sum():+.0f}" for s in SEAS)
    say(f"  {lab:52s} {w + l:4d} bets {w / max(w + l, 1):6.1%} {G.units.sum():+7.1f}u ({G.units.mean() * 100 if len(G) else 0:+5.1f}/100)  [{bys}]")
P = B[B.late & pre]
say("\nLate period, passing the other live filters (no home dog, not on tanking, not against 5-10)")
row(P[P.our_arr > 0], "our team has a recent arrival (trap)"); row(P[P.our_arr == 0], "no recent arrival")
say("\nReported, not tested")
row(P[P.opp_arr > 0], "late: opponent has a recent arrival")
E = B[~B.late & ~B.home_dog]
row(E[E.our_arr > 0], "Oct-Jan (no home dogs): our team has an arrival"); row(E[E.our_arr == 0], "Oct-Jan (no home dogs): none")
live_keep = pre & ~(B.late & (B.our_arr > 0))
row(B[live_keep], "FULL live filter (all three traps, no home dogs): kept"); row(B[~live_keep], "FULL live filter: removed")
row(B[B.kept.astype(bool)], "(Nov 6 filter test definition: kept)")

rng = np.random.default_rng(SEED)
A = {s: P[(P.season == s) & (P.our_arr > 0)].units.values for s in SEAS}; N = {s: P[(P.season == s) & (P.our_arr == 0)].units.values for s in SEAS}
d = np.array([np.concatenate([rng.choice(N[s], len(N[s])) for s in SEAS if len(N[s])]).mean()
              - np.concatenate([rng.choice(A[s], len(A[s])) for s in SEAS if len(A[s])]).mean() for _ in range(BOOT)])
ra, rn = P[P.our_arr > 0].units.mean(), P[P.our_arr == 0].units.mean()
say("\nPRIMARY TEST: ROI per bet, no-arrival minus arrival (late, other live filters passed)")
say(f"  arrival {ra * 100:+.1f}/100, none {rn * 100:+.1f}/100, difference {(rn - ra) * 100:+.1f}/100; bootstrap 10th percentile "
    f"{np.percentile(d, 10) * 100:+.1f}, 90% range {np.percentile(d, 5) * 100:+.1f} to {np.percentile(d, 95) * 100:+.1f}")
v = "REJECTED" if rn - ra <= 0 else ("CONFIRMED" if np.percentile(d, 10) > 0 and ra < 0 else "INCONCLUSIVE")
say(f"  VERDICT (pre-registered rule): {v}")
B.drop(columns="d").to_csv(os.path.join(W, "analysis", "arrival_trap_sbr_bets.csv"), index=False)
open(os.path.join(W, "analysis", "arrival_trap_sbr_output.txt"), "w").write("\n".join(out) + "\n")
