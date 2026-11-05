"""Where the money went, every game since 2019-20 (Nov 5, 2026; plan in betting-goals SHARP_MONEY.md).
Action Network's archive (v1 scoreboard, free, no key), one row per game: final consensus splits (% of bets = "public", % of money, number
of bets) for spread, total and moneyline, plus lines from the Open book, Consensus, DraftKings, FanDuel and the sharp-leaning offshore books
BetOnline, Westgate and Bovada (as last seen before the game), and the final score.
NOTE: the archive keeps ONE split per game (the last one before tip, close to the closing line), not its timing; the live tracker records timing.
  python sharp/backfill_splits.py WORKDIR --sport nba|nhl|ncaab|nfl|ncaaf [--threads 6] -> sharp/data/{sport}_splits.csv.gz"""
import os, sys, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
W = os.path.abspath(sys.argv[1]); ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
SPORT = ARG("--sport"); OUT = os.path.join(W, "sharp", "data"); os.makedirs(OUT, exist_ok=True)
BOOKS = {15: "cons", 30: "open", 68: "dk", 69: "fd", 1: "betonline", 14: "westgate", 21: "bovada"}
DIV = {"ncaab": "&division=D1", "ncaaf": "&division=FBS"}.get(SPORT, "")
def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}), timeout=30) as r: return json.loads(r.read())
        except Exception: time.sleep(2 + 3 * i)
    return {}
def rows(js):
    out = []
    for g in js.get("games", []):
        if g.get("status") != "complete": continue
        t = {x["id"]: x for x in g.get("teams", [])}; h, a = t.get(g["home_team_id"], {}), t.get(g["away_team_id"], {}); bx = g.get("boxscore") or {}
        r = dict(an_id=g["id"], start=g.get("start_time"), home=h.get("full_name"), away=a.get("full_name"), home_abbr=h.get("abbr"), away_abbr=a.get("abbr"),
                 home_pts=bx.get("total_home_points"), away_pts=bx.get("total_away_points"), num_bets=g.get("num_bets"))
        for o in g.get("odds") or []:
            b = BOOKS.get(o.get("book_id"))
            if not b or o.get("type") != "game": continue
            r.update({f"{b}_spread": o.get("spread_home"), f"{b}_spread_px": o.get("spread_home_line"), f"{b}_total": o.get("total"),
                      f"{b}_over_px": o.get("over"), f"{b}_ml_home": o.get("ml_home"), f"{b}_ml_away": o.get("ml_away"), f"{b}_at": o.get("inserted")})
            if b == "cons":
                for k in ("spread_home_public", "spread_home_money", "total_over_public", "total_over_money", "ml_home_public", "ml_home_money", "num_bets"):
                    r[k] = o.get(k)
        out.append(r)
    return out
if __name__ == "__main__":
    jobs = []
    if SPORT in ("nfl", "ncaaf"):
        weeks = range(1, 19) if SPORT == "nfl" else range(0, 17)
        for s in range(2019, 2027):
            jobs += [f"season={s}&week={w}" for w in weeks] + [f"season={s}&seasonType=post&week=1"] + ([f"season={s}&seasonType=post&week={w}" for w in (2, 3, 4)] if SPORT == "nfl" else [])
        urls = [f"https://api.actionnetwork.com/web/v1/scoreboard/{SPORT}?period=game&bookIds={','.join(map(str, BOOKS))}{DIV}&{q}" for q in jobs]
    else:
        months = {"nba": (10, 11, 12, 1, 2, 3, 4, 5, 6), "nhl": (10, 11, 12, 1, 2, 3, 4, 5, 6), "ncaab": (11, 12, 1, 2, 3, 4)}[SPORT]
        days = [d for d in pd.date_range("2019-10-01", pd.Timestamp.now().normalize() - pd.Timedelta(days=1)) if d.month in months]
        if SPORT in ("nba", "nhl"): days = [d for d in days if not (d.year == 2020 and d.month in (4, 5, 6))] + [d for d in pd.date_range("2020-07-25", "2020-10-15")]
        urls = [f"https://api.actionnetwork.com/web/v1/scoreboard/{SPORT}?period=game&bookIds={','.join(map(str, BOOKS))}{DIV}&date={d:%Y%m%d}" for d in sorted(set(days))]
    R = []
    with ThreadPoolExecutor(int(ARG("--threads", 6))) as ex:
        for i, r in enumerate(ex.map(lambda u: rows(get(u)), urls)):
            R += r
            if i % 300 == 0: print(SPORT, i, len(urls), len(R), flush=True)
    D = pd.DataFrame(R).drop_duplicates("an_id")
    D.to_csv(os.path.join(OUT, f"{SPORT}_splits.csv.gz"), index=False, compression="gzip")
    s = pd.to_datetime(D.start, utc=True); D["season"] = s.dt.year + (s.dt.month >= 8).astype(int)
    print(SPORT, "games", len(D), "with money split", D.spread_home_money.notna().sum(), "by season", D.groupby("season").spread_home_money.apply(lambda x: x.notna().sum()).to_dict(),
          "betonline lines", D.get("betonline_spread", pd.Series(dtype=float)).notna().sum())
