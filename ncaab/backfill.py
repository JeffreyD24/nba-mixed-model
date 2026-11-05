"""
NCAA men's basketball (Division I) history, free sources, no key (Nov 5, 2026).
For every date of each season from 2021-22 on:
  - Action Network (v1 scoreboard, D1): final scores, half scores, and full-game lines from the Open book (Action Network's
    opener), Consensus, DraftKings and FanDuel as last seen before tip (DK/FD from 2023-24 on; 2021-23 consensus only)
  - ESPN scoreboard (groups=50, all D-I): neutral-site flag and conference-game flag, matched to the Action Network game by
    date and final score (both teams' points)
  python ncaab/backfill.py WORKDIR [--from 2021-11-09] [--to 2026-11-04] [--threads 6]
Writes ncaab/data/games.csv (one row per game) and skips dates already saved (ncaab/data/dates_done.txt).
"""
import os, sys, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

W = os.path.abspath(sys.argv[1])
ARG = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
OUT = os.path.join(W, "ncaab", "data"); os.makedirs(OUT, exist_ok=True)
GAMES, DONE = os.path.join(OUT, "games.csv"), os.path.join(OUT, "dates_done.txt")
BOOKS = {15: "cons", 30: "open", 68: "dk", 69: "fd"}
HDR = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
SEASONS = [("2021-11-09", "2022-04-04"), ("2022-11-07", "2023-04-03"), ("2023-11-06", "2024-04-08"),
           ("2024-11-04", "2025-04-07"), ("2025-11-03", "2026-04-06"), ("2026-11-02", "2027-04-05")]


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30) as r: return json.loads(r.read())
        except Exception:
            if i == tries - 1: raise
            time.sleep(2 * (i + 1))


def season_of(day):
    d = pd.Timestamp(day); return d.year + (1 if d.month >= 8 else 0)


def one_day(day):
    d = pd.Timestamp(day)
    an = get(f"https://api.actionnetwork.com/web/v1/scoreboard/ncaab?period=game&bookIds=15,30,68,69&date={d:%Y%m%d}&division=D1")
    es = get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={d:%Y%m%d}&groups=50&limit=500")
    ek = {}
    for e in es.get("events", []):
        c = e["competitions"][0]; sc = {t["homeAway"]: int(float(t.get("score") or -1)) for t in c["competitors"]}
        info = dict(neutral=bool(c.get("neutralSite")), conf_game=bool(c.get("conferenceCompetition")), espn_id=e["id"])
        ek[(sc.get("home"), sc.get("away"))] = info; ek.setdefault((sc.get("away"), sc.get("home")), dict(info, flipped=True))
    rows = []
    for g in an.get("games", []):
        if g.get("status") != "complete": continue
        bx = g.get("boxscore") or {}; t = {x["id"]: x for x in g.get("teams", [])}
        h, a = t.get(g["home_team_id"]), t.get(g["away_team_id"])
        if not h or not a or bx.get("total_home_points") is None: continue
        hp, ap = int(bx["total_home_points"]), int(bx["total_away_points"])
        r = dict(date=str(d.date()), season=season_of(d), an_id=g["id"], start=g.get("start_time"), home_id=h["id"], away_id=a["id"],
                 home=h.get("full_name"), away=a.get("full_name"), home_conf=h.get("conference_type"), away_conf=a.get("conference_type"),
                 home_d1=h.get("division_type") == "D1", away_d1=a.get("division_type") == "D1", type=g.get("type"),
                 home_pts=hp, away_pts=ap, home_1h=bx.get("total_home_firsthalf_points"), away_1h=bx.get("total_away_firsthalf_points"),
                 periods=len(bx.get("linescore") or []))
        e = ek.get((hp, ap))
        r.update(neutral=(e or {}).get("neutral"), conf_game=(e or {}).get("conf_game"), espn_id=(e or {}).get("espn_id"),
                 espn_match=e is not None)
        for o in g.get("odds") or []:
            b = BOOKS.get(o.get("book_id"))
            if not b or o.get("type") != "game": continue
            r.update({f"{b}_spread": o.get("spread_home"), f"{b}_spread_px": o.get("spread_home_line"), f"{b}_spread_away_px": o.get("spread_away_line"),
                      f"{b}_total": o.get("total"), f"{b}_over_px": o.get("over"), f"{b}_under_px": o.get("under"),
                      f"{b}_ml_home": o.get("ml_home"), f"{b}_ml_away": o.get("ml_away"), f"{b}_at": o.get("inserted")})
        rows.append(r)
    return str(d.date()), rows


def main():
    lo, hi = pd.Timestamp(ARG("--from", SEASONS[0][0])), pd.Timestamp(ARG("--to", str(pd.Timestamp.now().date() - pd.Timedelta(days=1))))
    days = [x for a, b in SEASONS for x in pd.date_range(a, b) if lo <= x <= hi]
    done = set(open(DONE).read().split()) if os.path.exists(DONE) else set()
    todo = [x for x in days if str(x.date()) not in done]
    print(f"{len(todo)} dates to fetch ({len(done)} already saved)", flush=True)
    old = pd.read_csv(GAMES) if os.path.exists(GAMES) else None
    new, ok, n = [], [], 0
    with ThreadPoolExecutor(int(ARG("--threads", 6))) as ex:
        for res in ex.map(lambda x: (lambda: one_day(x))() if True else None, todo):
            day, rows = res; new += rows; ok.append(day); n += 1
            if n % 50 == 0: print(f"  {n}/{len(todo)} dates, {len(new)} games", flush=True)
    G = pd.concat([old, pd.DataFrame(new)], ignore_index=True) if old is not None else pd.DataFrame(new)
    G = G.drop_duplicates("an_id", keep="last").sort_values(["date", "start"])
    G.to_csv(GAMES, index=False); open(DONE, "a").write("".join(f"{d}\n" for d in ok))
    print(f"saved {len(G)} games; ESPN match {G.espn_match.mean():.1%}; neutral {G.neutral.fillna(False).astype(bool).mean():.1%}; "
          f"DK lines {G.get('dk_spread', pd.Series(dtype=float)).notna().sum()}", flush=True)


if __name__ == "__main__":
    main()
