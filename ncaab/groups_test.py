"""NCAAM team-groups test (ncaab/research/GROUPS_PREREG_2026-11-05.md). Needs ncaab/data/espn_meta.csv, sbr_games.csv, games.csv.
  python ncaab/groups_test.py WORKDIR -> ncaab/research/groups_output.txt, ncaab/data/groups_games.csv"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1]); D = os.path.join(W, "ncaab", "data"); out = []
def say(*a): out.append(" ".join(str(x) for x in a)); print(*a, flush=True)
M = pd.read_csv(os.path.join(D, "espn_meta.csv"), low_memory=False)
M = M.dropna(subset=["home_pts", "away_pts"]); M["home_pts"] = M.home_pts.astype(int); M["away_pts"] = M.away_pts.astype(int)
M["season"] = pd.to_datetime(M.date).pipe(lambda d: d.dt.year + (d.dt.month >= 8))
POWER = {2, 4, 7, 8, 21, 23}
HOUSE = {"Kentucky", "Kansas", "Duke", "North Carolina", "UCLA", "Indiana", "Michigan State", "Villanova", "Gonzaga", "UConn", "Louisville",
         "Arizona", "Syracuse", "Florida"}
COACH = [("Michigan State", 0, 9999), ("Kansas", 0, 9999), ("Gonzaga", 0, 9999), ("Baylor", 0, 9999), ("Duke", 0, 2022), ("Kentucky", 2010, 2024),
         ("Arkansas", 2025, 9999), ("North Carolina", 0, 2021), ("Villanova", 0, 2022), ("Syracuse", 0, 2023), ("Louisville", 0, 2017),
         ("St. John's", 2024, 9999), ("Virginia", 2010, 2024), ("UConn", 2019, 9999), ("Houston", 2015, 9999), ("Texas", 0, 2015),
         ("Tennessee", 2016, 9999), ("Auburn", 2015, 2025)]
coach = lambda loc, s: any(loc == l and a <= s <= b for l, a, b in COACH)
for s in ("home", "away"):
    M[f"{s}_ranked"] = M[f"{s}_rank"].fillna(99).astype(int) <= 25
    M[f"{s}_power"] = M[f"{s}_conf_id"].isin(POWER)
    M[f"{s}_house"] = M[f"{s}_loc"].isin(HOUSE)
    M[f"{s}_coach"] = [coach(l, se) for l, se in zip(M[f"{s}_loc"], M.season)]
GRP = ["ranked", "power", "house", "coach"]
# ---- old seasons: SBR matched by date + both scores (either orientation); dates with duplicate score pairs dropped
Sb = pd.read_csv(os.path.join(D, "sbr_games.csv"))
key = lambda d, a, b: (d, min(a, b), max(a, b))
M["k"] = [key(d, a, b) for d, a, b in zip(M.date, M.home_pts, M.away_pts)]; Sb["k"] = [key(d, int(a), int(b)) for d, a, b in zip(Sb.date, Sb.home_pts, Sb.away_pts)]
M1 = M[~M.k.duplicated(keep=False)].set_index("k"); Sb = Sb[~Sb.k.duplicated(keep=False)]
J = Sb.join(M1[[c for c in M1.columns if c not in ("date", "season", "home_pts", "away_pts")] + ["home_pts", "away_pts"]], on="k", rsuffix="_e", how="inner")
flip = J.home_pts != J.home_pts_e                      # SBR's home is ESPN's away: swap the group flags
for g in GRP + ["rank", "loc"]:
    h, a = J[f"home_{g}"].copy(), J[f"away_{g}"].copy(); J.loc[flip, f"home_{g}"] = a[flip]; J.loc[flip, f"away_{g}"] = h[flip]
J["close_sp"], J["close_tot"], J["src"] = J.close_spread, J.close_total, "SBR"
say(f"SBR matched to ESPN: {len(J)} of {len(Sb)} unambiguous games ({len(J) / len(Sb):.0%})")
# ---- recent seasons: Action Network file joined on ESPN id; consensus close 2022-23, DraftKings close 2024-26
A = pd.read_csv(os.path.join(D, "games.csv"), low_memory=False); A = A[A.espn_id.notna()].copy(); A["espn_id"] = A.espn_id.astype(int)
M2 = M.drop_duplicates("espn_id").set_index("espn_id")
A = A.join(M2[[c for c in M2.columns if any(c.startswith(p) for p in ("home_", "away_")) and c not in ("home_pts", "away_pts")] + ["conf_game"]].add_suffix("_e"), on="espn_id", how="inner")
for g in GRP + ["rank", "loc"]: A[f"home_{g}"], A[f"away_{g}"] = A[f"home_{g}_e"], A[f"away_{g}_e"]
A["conf_game"] = A.conf_game_e
A["close_sp"] = np.where(A.season >= 2024, A.dk_spread, A.cons_spread); A["close_tot"] = np.where(A.season >= 2024, A.dk_total, A.cons_total)
A["src"] = np.where(A.season >= 2024, "DK", "consensus"); A["neutral"] = A.neutral.astype(str) == "True"
cols = ["season", "date", "home_pts", "away_pts", "close_sp", "close_tot", "src", "conf_game", "neutral"] + [f"{s}_{g}" for s in ("home", "away") for g in GRP + ["rank", "loc"]]
G = pd.concat([J[cols], A[cols]], ignore_index=True)
G["conf_game"] = G.conf_game.astype(str) == "True"
for g in GRP: G[f"home_{g}"] = G[f"home_{g}"].astype(bool); G[f"away_{g}"] = G[f"away_{g}"].astype(bool)
G.to_csv(os.path.join(D, "groups_games.csv"), index=False)
say(f"games with groups and a close: {G.close_sp.notna().sum()} spreads, {G.close_tot.notna().sum()} totals; by season {G.groupby('season').size().to_dict()}")
m = G.home_pts - G.away_pts; t = G.home_pts + G.away_pts
home_cov = np.sign(m + G.close_sp)                      # +1 home covers the close, -1 away covers, 0 push
over = np.sign(t - G.close_tot)
def side_cell(only_one, g, extra=None):
    """cover of the group team (exactly one team in the group): +1 covers, -1 doesn't"""
    h, a = G[f"home_{g}"], G[f"away_{g}"]
    k = (h ^ a) & G.close_sp.notna(); res = np.where(h, home_cov, -home_cov)
    if extra is not None: k = k & extra
    return k, pd.Series(res, index=G.index)
gsp = lambda g: pd.Series(np.where(G[f"home_{g}"], G.close_sp, -G.close_sp), index=G.index)   # group team's own spread
CELLS = {}
k, r = side_cell(1, "ranked"); CELLS["S1 ranked vs unranked"] = ("spread", k, r)
k, r = side_cell(1, "ranked", gsp("ranked") <= -10); CELLS["S2 ranked favored by 10+ vs unranked"] = ("spread", k, r)
k, r = side_cell(1, "power"); CELLS["S3 power-conference vs non-power"] = ("spread", k, r)
k, r = side_cell(1, "house"); CELLS["S4 powerhouse vs non-powerhouse"] = ("spread", k, r)
k, r = side_cell(1, "coach"); CELLS["S5 elite-coach team vs others"] = ("spread", k, r)
CELLS["S6 both ranked: home team"] = ("spread", G.home_ranked & G.away_ranked & G.close_sp.notna() & ~G.neutral, pd.Series(home_cov, index=G.index))
ot = lambda k: ("total", k & G.close_tot.notna(), pd.Series(over, index=G.index))
CELLS["T1 both power conference"] = ot(G.home_power & G.away_power)
CELLS["T2 any ranked team"] = ot(G.home_ranked | G.away_ranked)
CELLS["T3 any powerhouse"] = ot(G.home_house | G.away_house)
CELLS["T4 any elite-coach team"] = ot(G.home_coach | G.away_coach)
CELLS["T5 neither team power conference"] = ot(~G.home_power & ~G.away_power)
CELLS["T6 conference game"] = ot(G.conf_game)
disc = G.season <= 2018; hold = G.season >= 2019; dk = G.season >= 2024
def rate(k, r):
    x = r[k]; x = x[x != 0]; n = len(x); p = (x > 0).mean() if n else np.nan
    return n, p, (p - 0.5) / np.sqrt(0.25 / n) if n else np.nan
say("\nDISCOVERY 2007-08..2017-18 (|z| >= 2.64 to qualify) -> HOLDOUT 2018-19..2025-26 (same direction, >= 52.4%, z >= 1.65, DK 2023-26 >= 50%)")
say(f"{'cell':40s} {'disc n':>7s} {'rate':>6s} {'z':>6s} | {'hold n':>6s} {'rate':>6s} | DK 23-26 | decision")
for name, (mk, k, r) in CELLS.items():
    n1, p1, z1 = rate(k & disc, r); n2, p2, z2 = rate(k & hold, r); n3, p3, _ = rate(k & dk, r)
    if abs(z1) >= 2.64:
        d = 1 if p1 > 0.5 else -1; q2, q3 = (p2 if d > 0 else 1 - p2), (p3 if d > 0 else 1 - p3); zz = (q2 - 0.5) / np.sqrt(0.25 / n2)
        what = ("back" if d > 0 else "fade") if mk == "spread" else ("over" if d > 0 else "under")
        dec = f"{what}: holdout {q2:.1%} z {zz:+.2f}, DK {q3:.1%} -> " + ("PASS" if q2 >= 0.524 and zz >= 1.65 and q3 >= 0.5 else "FAIL")
    else: dec = "not qualified"
    say(f"{name:40s} {n1:7d} {p1:6.1%} {z1:+6.2f} | {n2:6d} {p2:6.1%} | {p3:6.1%} ({n3}) | {dec}")
open(os.path.join(W, "ncaab", "research", "groups_output.txt"), "w").write("\n".join(out) + "\n")
