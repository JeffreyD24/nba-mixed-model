"""Free sportsbook openers + closers for every D-I NCAAM game with lines (copy of nfl-mixed-model ncaaf/espn_openers.py) from ESPN's odds feed (Nov 5, 2026). One request per game
(ESPN event id from ncaaf/data/games.csv). Each provider ESPN lists (ESPN BET for 2024-25; DraftKings and ~10 books for 2023 from
week 8; DraftKings for the 2025 postseason) with its opening and closing home spread and total. No timestamps on openers.
Light use only (personal research, a few requests per second at most).
  python ncaab/espn_openers.py WORKDIR [--seasons 2024,2025,2026] -> ncaab/data/espn_openers.csv"""
import os, sys, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
W = os.path.abspath(sys.argv[1]); ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
OUT = ARG("--out", os.path.join(W, "ncaab", "data", "espn_openers.csv"))
URL = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/events/{e}/competitions/{e}/odds?limit=50"
num = lambda x: (lambda v: v)(float(str(x).replace("+", ""))) if x not in (None, "", "EVEN", "even") else None


def get(u):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r: return json.loads(r.read())
        except Exception:
            time.sleep(1 + 2 * i)
    return None


def one(e):
    d = get(URL.format(e=e)); rows = []
    for it in (d or {}).get("items", []):
        p = it.get("provider", {}); h = it.get("homeTeamOdds", {}) or {}
        g = lambda o, *ks: (lambda x: x)(__import__("functools").reduce(lambda a, k: (a or {}).get(k), ks, o))
        try:
            rows.append(dict(espn_id=e, provider_id=p.get("id"), provider=p.get("name"),
                             open_spread=num(g(h, "open", "pointSpread", "american")), close_spread=num(g(h, "close", "pointSpread", "american")),
                             open_spread_px=num(g(h, "open", "spread", "american")), close_spread_px=num(g(h, "close", "spread", "american")),
                             open_total=num(g(it, "open", "total", "american")), close_total=num(g(it, "close", "total", "american")),
                             open_over_px=num(g(it, "open", "over", "american")), close_over_px=num(g(it, "close", "over", "american")),
                             home_fav_open=g(h, "open", "favorite")))
        except Exception:
            pass
    time.sleep(0.1)
    return rows


if __name__ == "__main__":
    seasons = [int(x) for x in ARG("--seasons", "2024,2025,2026").split(",")]
    G = pd.read_csv(os.path.join(W, "ncaab", "data", "games.csv"), low_memory=False)
    ids = sorted(set(G[G.season.isin(seasons) & G.espn_id.notna() & G.home_d1.astype(bool) & G.away_d1.astype(bool) & G.dk_spread.notna()].espn_id.astype(int)))
    print(len(ids), "games", flush=True); rows = []
    with ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(one, ids)):
            rows += r
            if i % 500 == 0: print(" ", i, flush=True)
    R = pd.DataFrame(rows); R.to_csv(OUT, index=False)
    print(R.groupby("provider").agg(games=("espn_id", "nunique"), open_spread=("open_spread", lambda x: x.notna().sum()), open_total=("open_total", lambda x: x.notna().sum())).sort_values("games", ascending=False).head(12))
