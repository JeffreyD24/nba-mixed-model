"""
NBA second half (Feb-Apr): spreads by what each team is playing for and how its roster changed.
Before every game (no lookahead): conference rank by win %, games behind 10th, and a category
  top      = ranks 1-4
  middle   = ranks 5-10 (playoff / play-in spots)
  bubble   = ranks 11-12 within 4 games of 10th
  tanking  = ranks 13-15, or 11-12 more than 4 games behind 10th
Roster: recent arrival (a 12+ min/game player who played for another team earlier this season, first game here in the last
30 days), key player back (injured value at the open is 1.0+ lower than at the team's previous game), roster strength change.
  1. MARKET: home cover margin vs the closing spread, Feb-Apr 2021-22..2025-26, by matchup
  2. OUR BETS: the live spread model's bets at DraftKings openers, Feb-Apr 2023-24..2025-26, by our team's / opponent's category
  python analysis/late_season.py WORKDIR
"""
import os, sys
import numpy as np, pandas as pd
W = os.path.abspath(sys.argv[1])
EAST = {"atl", "bos", "bkn", "cha", "chi", "cle", "det", "ind", "mia", "mil", "ny", "orl", "phi", "tor", "wsh"}
T = pd.read_csv(os.path.join(W, "data", "training_games.csv")).sort_values("date").reset_index(drop=True)
# ---- standings before each game date
rows = []
for r in T.itertuples():
    rows += [dict(season=r.season, date=r.date, team=r.home, w=int(r.home_pts > r.away_pts)), dict(season=r.season, date=r.date, team=r.away, w=int(r.away_pts > r.home_pts))]
L = pd.DataFrame(rows)
cat = {}
for s, S in L.groupby("season"):
    for d in sorted(S.date.unique()):
        past = S[S.date < d].groupby("team").w.agg(["sum", "size"])
        if len(past) < 30: continue
        past["l"] = past["size"] - past["sum"]; past["wp"] = past["sum"] / past["size"]
        for conf in (True, False):
            c = past[past.index.isin(EAST) == conf].sort_values("wp", ascending=False)
            c["rank"] = np.arange(1, len(c) + 1)
            w10, l10 = c.iloc[9]["sum"], c.iloc[9]["l"]
            c["gb10"] = ((w10 - l10) - (c["sum"] - c.l)) / 2
            for t, x in c.iterrows():
                k = ("top" if x["rank"] <= 4 else "middle" if x["rank"] <= 10 else
                     "bubble" if (x["rank"] <= 12 and x.gb10 <= 4) else "tanking")
                cat[(d, t)] = (k, int(x["rank"]), float(x.gb10), float(x.wp))
for side in ("home", "away"):
    T[f"{side[0]}_cat"] = [cat.get((d, t), (None,))[0] for d, t in zip(T.date, T[side])]
    T[f"{side[0]}_rank"] = [cat.get((d, t), (None, np.nan))[1] for d, t in zip(T.date, T[side])]
# ---- key player back: injured value at the open vs the team's previous game (final report)
inj = []
for r in T.itertuples():
    inj += [dict(i=r.Index, season=r.season, team=r.home, side="h", now=r.home_miss_off_open + r.home_miss_def_open, fin=r.home_miss_off + r.home_miss_def),
            dict(i=r.Index, season=r.season, team=r.away, side="a", now=r.away_miss_off_open + r.away_miss_def_open, fin=r.away_miss_off + r.away_miss_def)]
I = pd.DataFrame(inj).sort_values(["season", "team", "i"]); I["prev_fin"] = I.groupby(["season", "team"]).fin.shift()
I["back"] = (I.prev_fin - I.now) >= 1.0; I["lost"] = (I.now - I.prev_fin) >= 1.0
for c in ("back", "lost"):
    pv = I.pivot_table(index="i", columns="side", values=c, aggfunc="first"); T[f"h_{c}"] = pv["h"].reindex(T.index).fillna(False).astype(bool); T[f"a_{c}"] = pv["a"].reindex(T.index).fillna(False).astype(bool)
# ---- recent arrivals (trades / signings) from player game logs
PG = pd.read_csv("/home/claude/data/espn_player_games_2023_2026.csv", low_memory=False)
PG = PG[PG.season_type.astype(str).str.contains("Regular")].copy(); PG["minutes"] = pd.to_numeric(PG.minutes, errors="coerce"); PG = PG[PG.minutes > 0]
codes = {"GS": "gs", "NO": "no", "NY": "ny", "SA": "sa", "UTAH": "utah", "WSH": "wsh"}
PG["team"] = PG.team.map(lambda t: codes.get(t, str(t).lower())); PG["date"] = pd.to_datetime(PG.game_date)
first_season = PG.groupby(["season", "espn_player_id"]).date.min()
first_team = PG.groupby(["season", "espn_player_id", "team"]).agg(t0=("date", "min"), mpg=("minutes", "mean"), gp=("minutes", "size")).reset_index()
first_team["season_first"] = [first_season[(s, p)] for s, p in zip(first_team.season, first_team.espn_player_id)]
arr = first_team[(first_team.t0 > first_team.season_first + pd.Timedelta(days=3)) & (first_team.mpg >= 12) & (first_team.gp >= 3)]
def recent_arrivals(season, team, d):
    a = arr[(arr.season == season) & (arr.team == team) & (arr.t0 < d) & (arr.t0 >= d - pd.Timedelta(days=30))]
    return len(a)
T["d"] = pd.to_datetime(T.date)
T["h_arr"] = [recent_arrivals(s, t, d) for s, t, d in zip(T.season, T.home, T.d)]
T["a_arr"] = [recent_arrivals(s, t, d) for s, t, d in zip(T.season, T.away, T.d)]
R = pd.read_csv(os.path.join(W, "analysis", "roster_strength.csv"))
for side in ("home", "away"):
    T = T.merge(R[["date", "team", "delta"]].rename(columns={"team": side, "delta": f"{side[0]}_rd"}), on=["date", side], how="left")
T["late"] = T.d.dt.month.isin([2, 3, 4]); T["cover"] = T.home_pts - T.away_pts + T.spread
T.to_csv(os.path.join(W, "analysis", "late_season_games.csv"), index=False)

def show(lab, g, y="cover"):
    se = g[y].std() / np.sqrt(max(len(g), 1))
    per = " ".join(f"{s % 100}:{g[g.season == s][y].mean():+.1f}" for s in sorted(g.season.unique()))
    print(f"  {lab:44s} n={len(g):4d} home covers by {g[y].mean():+5.2f} (+/- {se:.2f})  [{per}]")
G = T[T.late & T.h_cat.notna()]
print("1. MARKET, Feb-Apr 2021-22..2025-26: home cover margin vs the closing spread, by matchup (home vs away category)")
for (hc, ac), g in G.groupby(["h_cat", "a_cat"]):
    if len(g) >= 40: show(f"home {hc:8s} vs away {ac}", g)
print("\n  by one team's situation (home side shown; + = home beat the close)")
for lab, k in (("home team tanking", G.h_cat == "tanking"), ("away team tanking", G.a_cat == "tanking"),
               ("home team on the bubble", G.h_cat == "bubble"), ("away team on the bubble", G.a_cat == "bubble"),
               ("home team top-4", G.h_cat == "top"), ("away team top-4", G.a_cat == "top"),
               ("home team: recent arrival(s)", G.h_arr > 0), ("away team: recent arrival(s)", G.a_arr > 0),
               ("home team: key player back", G.h_back), ("away team: key player back", G.a_back),
               ("home team: key player newly out", G.h_lost), ("away team: key player newly out", G.a_lost)):
    show(lab, G[k])
print("\n  same, Oct-Jan for comparison")
G2 = T[~T.late & T.h_cat.notna()]
for lab, k in (("home team tanking", G2.h_cat == "tanking"), ("away team tanking", G2.a_cat == "tanking"),
               ("home team: key player back", G2.h_back), ("away team: key player back", G2.a_back),
               ("home team: recent arrival(s)", G2.h_arr > 0), ("away team: recent arrival(s)", G2.a_arr > 0)):
    show(lab, G2[k])

# ---- our bets
B = pd.read_csv(os.path.join(W, "analysis", "half_compare_bets.csv"))
B = B.merge(T[["date", "home", "away", "h_cat", "a_cat", "h_rank", "a_rank", "h_back", "a_back", "h_lost", "a_lost", "h_arr", "a_arr"]], on=["date", "home", "away"], how="left")
hb = B.home_bet.astype(bool)
B["our_cat"] = np.where(hb, B.h_cat, B.a_cat); B["opp_cat"] = np.where(hb, B.a_cat, B.h_cat)
B["our_back"] = np.where(hb, B.h_back, B.a_back); B["opp_back"] = np.where(hb, B.a_back, B.h_back)
B["our_arr"] = np.where(hb, B.h_arr, B.a_arr); B["opp_arr"] = np.where(hb, B.a_arr, B.h_arr)
B["our_lost"] = np.where(hb, B.h_lost, B.a_lost); B["opp_lost"] = np.where(hb, B.a_lost, B.h_lost)
def s_(g):
    n = len(g); w = g.won.sum(); per = " ".join(f"{s % 100}:{(lambda x: x.won.sum() * 100 / 110 - (~x.won.astype(bool)).sum())(g[g.season == s]):+.0f}" for s in (2024, 2025, 2026))
    return f"{n:4d} bets {w / max(n, 1):.1%} {w * 100 / 110 - (n - w):+6.1f}u  [{per}]"
for half, H in (("Feb-Apr", B[B.late]), ("Oct-Jan", B[~B.late])):
    print(f"\n2. OUR SPREAD BETS, {half} (live spread model, DK openers, edge 3+): {s_(H)}")
    print("  by OUR team's situation"); [print(f"    we bet a {k:9s} team      {s_(g)}") for k, g in H.groupby("our_cat")]
    print("  by the OPPONENT's situation"); [print(f"    against a {k:9s} team     {s_(g)}") for k, g in H.groupby("opp_cat")]
    print("  matchups (ours vs theirs, 25+ bets)")
    for (a, b_), g in H.groupby(["our_cat", "opp_cat"]):
        if len(g) >= 25: print(f"    {a:8s} vs {b_:8s}             {s_(g)}")
    for lab, k in (("our team has a recent arrival", H.our_arr > 0), ("opponent has a recent arrival", H.opp_arr > 0),
                   ("our team getting a key player back", H.our_back.astype(bool)), ("opponent getting a key player back", H.opp_back.astype(bool)),
                   ("our team just lost a key player", H.our_lost.astype(bool)), ("opponent just lost a key player", H.opp_lost.astype(bool))):
        print(f"    {lab:36s} {s_(H[k])}")
B.to_csv(os.path.join(W, "analysis", "late_season_bets.csv"), index=False)
