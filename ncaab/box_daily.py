"""NCAAM daily box scores for the current season (Nov 5, 2026; needed by the stale-line rule v2's lineup and roster features, ncaab/layer_features.py).
Fetches ESPN player and team box scores for this season's games from the last 3 days, plus any earlier game this season still missing
(up to 400 a run), with the same parser as the backfill (ncaab/espn_boxscores.py), and merges them into ncaab/data/box/{players,teams}_{season}.csv.gz.
Runs in the morning job after ncaab/m2_daily.py has refreshed ncaab/data/espn_meta.csv.
  python ncaab/box_daily.py WORKDIR"""
import os, sys, importlib.util
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
W = os.path.abspath(sys.argv[1]); BOX = os.path.join(W, "ncaab", "data", "box")
M = pd.read_csv(os.path.join(W, "ncaab", "data", "espn_meta.csv"), low_memory=False)
d = pd.to_datetime(M.date); M["season"] = d.dt.year + (d.dt.month >= 8).astype(int); M["d"] = d
today = pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None); cur = int(M.season[M.d < today].max())
sys.argv = ["x", W, "--season", str(cur)]
spec = importlib.util.spec_from_file_location("eb", os.path.join(W, "ncaab", "espn_boxscores.py")); eb = importlib.util.module_from_spec(spec); spec.loader.exec_module(eb)
PF, TF = os.path.join(BOX, f"players_{cur}.csv.gz"), os.path.join(BOX, f"teams_{cur}.csv.gz")
P = pd.read_csv(PF) if os.path.exists(PF) else pd.DataFrame(columns=["espn_id", "team_id", "athlete_id", "name", "starter", "min", "pts"])
T = pd.read_csv(TF) if os.path.exists(TF) else pd.DataFrame()
played = M[(M.season == cur) & (M.d < today)]
recent = set(played[played.d >= today - pd.Timedelta(days=3)].espn_id.astype(int))
missing = set(played.espn_id.astype(int)) - set(P.espn_id.astype(int)) if len(P) else set(played.espn_id.astype(int))
ids = sorted(recent | set(sorted(missing)[-400:]))
Pn, Tn = [], []
with ThreadPoolExecutor(6) as ex:
    for p, t in ex.map(eb.one, ids): Pn += p; Tn += t
Pn = pd.DataFrame(Pn, columns=["espn_id", "team_id", "athlete_id", "name", "starter", "min", "pts"]); Tn = pd.DataFrame(Tn)
got = set(Pn.espn_id.astype(int)) if len(Pn) else set()
if got:
    P = pd.concat([P[~P.espn_id.astype(int).isin(got)], Pn], ignore_index=True); P.to_csv(PF, index=False, compression="gzip")
    if len(Tn): T = pd.concat([T[~T.espn_id.astype(int).isin(got)], Tn], ignore_index=True) if len(T) else Tn; T.to_csv(TF, index=False, compression="gzip")
print(f"NCAAM box scores {cur}: asked {len(ids)} games, got {len(got)}; season file now {P.espn_id.nunique()} games")
