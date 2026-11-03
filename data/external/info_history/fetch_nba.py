"""
NBA player game logs (who played, minutes, starters) 2010-11 .. present, for "who missed the last game".

    python3 -I fetch_nba.py 2011 2012 ...      season = year it ends. No args = 2011..2027.

Source order per season:
  1. stats.nba.com `leaguegamelog` (player level): ONE request per season, all games. Cloud IPs are sometimes blocked
     by stats.nba.com (the repo's tracking backfill had timeouts), so it gets 3 tries with a long timeout.
  2. If that fails: ESPN (same source the repo's rotations.py uses): scoreboard per date -> summary per game. ~1,300 requests/season.

Writes nba/player_games_YYYY.csv (game_id, date, team, opp, home, player_id, name, minutes, pts, started, dnp_reason, source)
and nba/fetch_log.csv (which source worked per season). `started` is only known from ESPN; leaguegamelog has no starter flag.
"""
import csv, json, os, sys, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "nba"); os.makedirs(OUT, exist_ok=True)
COLS = ["game_id", "date", "team", "opp", "home", "player_id", "name", "minutes", "pts", "started", "dnp_reason", "source"]
NBA_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
               "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com", "Accept": "application/json",
               "x-nba-stats-origin": "stats", "x-nba-stats-token": "true"}


def get(url, headers=None, timeout=40, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0 sports-research"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            if k == tries - 1: raise
            time.sleep(3 * (k + 1))


def from_nba_stats(season):
    ss = f"{season - 1}-{str(season)[2:]}"
    q = urllib.parse.urlencode(dict(Counter=0, DateFrom="", DateTo="", Direction="ASC", LeagueID="00", PlayerOrTeam="P", Season=ss,
                                    SeasonType="Regular Season", Sorter="DATE"))
    d = get(f"https://stats.nba.com/stats/leaguegamelog?{q}", NBA_HEADERS, timeout=90)
    rs = d["resultSets"][0]; h = rs["headers"]; rows = []
    for r in rs["rowSet"]:
        x = dict(zip(h, r)); m = x["MATCHUP"]; home = " vs. " in m
        rows.append(dict(game_id=x["GAME_ID"], date=x["GAME_DATE"], team=x["TEAM_ABBREVIATION"], opp=m.split()[-1], home=home,
                         player_id=x["PLAYER_ID"], name=x["PLAYER_NAME"], minutes=x["MIN"], pts=x["PTS"], started="", dnp_reason="", source="nba_stats"))
    return rows


ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"


def espn_game(ev):
    try:
        d = get(f"{ESPN}/summary?event={ev['id']}")
        date = ev["date"][:10]; teams = d["boxscore"]["players"]
        ab = [t["team"]["abbreviation"] for t in teams]; rows = []
        for i, t in enumerate(teams):
            side = next((c["homeAway"] for c in ev["competitions"][0]["competitors"] if c["team"]["abbreviation"] == ab[i]), "")
            for blk in t.get("statistics", []):
                keys = blk.get("keys") or blk.get("names") or []
                for a in blk.get("athletes", []):
                    st = dict(zip(keys, a.get("stats", []))); ath = a["athlete"]
                    played = not a.get("didNotPlay", False)
                    rows.append(dict(game_id=ev["id"], date=date, team=ab[i], opp=ab[1 - i], home=side == "home", player_id=ath.get("id"),
                                     name=ath.get("displayName"), minutes=st.get("minutes", "") if played else 0, pts=st.get("points", "") if played else "",
                                     started=a.get("starter", ""), dnp_reason=a.get("reason", "") if not played else "", source="espn"))
        return rows, None
    except Exception as e:
        return [], f"{ev['id']}: {type(e).__name__} {str(e)[:80]}"


def from_espn(season, errs):
    d = dt.date(season - 1, 10, 1); end = dt.date(season, 4, 20); events = {}
    while d <= end:
        try:
            sb = get(f"{ESPN}/scoreboard?dates={d.strftime('%Y%m%d')}&limit=100")
            for ev in sb.get("events", []):
                if ev.get("season", {}).get("type") == 2 and ev["status"]["type"]["completed"]:
                    events[ev["id"]] = ev
        except Exception as e:
            errs.append(f"scoreboard {d}: {str(e)[:60]}")
        d += dt.timedelta(days=1)
    rows = []
    with ThreadPoolExecutor(4) as ex:
        for r, err in ex.map(espn_game, list(events.values())):
            rows.extend(r)
            if err: errs.append(err)
    return rows


def main():
    seasons = [int(x) for x in sys.argv[1:]] or list(range(2011, 2028))
    log = []
    for s in seasons:
        path = os.path.join(OUT, f"player_games_{s}.csv")
        if os.path.exists(path) and s < dt.date.today().year:      # finished seasons are fetched once
            print("skip", s); continue
        errs = []; src = "nba_stats"
        try:
            rows = from_nba_stats(s)
        except Exception as e:
            print(f"season {s}: stats.nba.com failed ({type(e).__name__}: {str(e)[:60]}), using ESPN", flush=True)
            src = "espn"; rows = from_espn(s, errs)
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
        log.append(dict(season=s, source=src, rows=len(rows), errors=len(errs), first_error=errs[0] if errs else ""))
        print(log[-1], flush=True)
    lp = os.path.join(OUT, "fetch_log.csv"); new = not os.path.exists(lp)
    with open(lp, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["season", "source", "rows", "errors", "first_error"])
        if new: w.writeheader()
        w.writerows(log)


if __name__ == "__main__":
    main()
