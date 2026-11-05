"""ESPN player and team box scores for every NCAAM game of a season (Nov 5, 2026): the base for lineup / injury / travel models.
Per game: each player's team, starter flag, minutes, points (players file); team totals FGA, FTA, OREB, TO, FGM, 3PA (possessions /
tempo) and the venue city, state and attendance (teams file). Event ids from ncaab/data/espn_meta.csv. Light use, a few requests a second.
  python ncaab/espn_boxscores.py WORKDIR --season 2026 [--threads 6] [--limit N]
  -> ncaab/data/box/players_{season}.csv.gz, ncaab/data/box/teams_{season}.csv.gz"""
import os, sys, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
W = os.path.abspath(sys.argv[1]); ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
SEASON = int(ARG("--season")); OUT = os.path.join(W, "ncaab", "data", "box"); os.makedirs(OUT, exist_ok=True)
U = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary?event={e}"
def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r: return json.loads(r.read())
        except Exception: time.sleep(2 + 3 * i)
    return None
def num(x):
    try: return float(str(x).split("-")[0]) if x not in (None, "", "--") else None
    except ValueError: return None
def made_att(x):
    try: a, b = str(x).split("-"); return float(a), float(b)
    except Exception: return None, None
def one(e):
    d = get(U.format(e=e)); P, T = [], []
    if not d: return P, T
    gi = d.get("gameInfo") or {}; ad = (gi.get("venue") or {}).get("address") or {}
    for t in (d.get("boxscore") or {}).get("players", []):
        tid = t["team"]["id"]; st = (t.get("statistics") or [{}])[0]; lab = st.get("labels") or []
        ix = {l: i for i, l in enumerate(lab)}; tot = {"FGA": 0, "FGM": 0, "3PA": 0, "FTA": 0, "OREB": 0, "TO": 0, "MIN": 0}
        for a in st.get("athletes", []):
            s = a.get("stats") or []
            if not s: continue
            g = lambda k: s[ix[k]] if k in ix and ix[k] < len(s) else None
            mn = num(g("MIN")); pts = num(g("PTS"))
            P.append((e, tid, a["athlete"].get("id"), a["athlete"].get("displayName"), int(bool(a.get("starter"))), mn, pts))
            fgm, fga = made_att(g("FG")); _, tpa = made_att(g("3PT")); _, fta = made_att(g("FT"))
            for k, v in (("FGA", fga), ("FGM", fgm), ("3PA", tpa), ("FTA", fta), ("OREB", num(g("OREB"))), ("TO", num(g("TO"))), ("MIN", mn)):
                if v is not None: tot[k] += v
        T.append(dict(espn_id=e, team_id=tid, **tot, city=ad.get("city"), state=ad.get("state"), venue_id=(gi.get("venue") or {}).get("id"), attendance=gi.get("attendance")))
    time.sleep(0.1)
    return P, T
if __name__ == "__main__":
    M = pd.read_csv(os.path.join(W, "ncaab", "data", "espn_meta.csv"), low_memory=False)
    d = pd.to_datetime(M.date); M["season"] = d.dt.year + (d.dt.month >= 8).astype(int)
    ids = sorted(set(M[M.season == SEASON].espn_id.astype(int)))
    if ARG("--limit"): ids = ids[: int(ARG("--limit"))]
    P, T = [], []
    with ThreadPoolExecutor(int(ARG("--threads", 6))) as ex:
        for i, (p, t) in enumerate(ex.map(one, ids)):
            P += p; T += t
            if i % 1000 == 0: print(SEASON, i, len(ids), flush=True)
    pd.DataFrame(P, columns=["espn_id", "team_id", "athlete_id", "name", "starter", "min", "pts"]).to_csv(os.path.join(OUT, f"players_{SEASON}.csv.gz"), index=False, compression="gzip")
    pd.DataFrame(T).to_csv(os.path.join(OUT, f"teams_{SEASON}.csv.gz"), index=False, compression="gzip")
    print(f"season {SEASON}: {len(ids)} games, {len(P)} player rows, {len(T)} team rows")
