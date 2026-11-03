"""
NHL box scores (who played, goalies, who started) from the public NHL API, 2010-11 .. present. Resumable.

    python3 -I fetch_nhl.py 2011 2012 ...      season = year it ends (2011 = 2010-11). No args = 2011..2027.

Writes nhl/:
  games_YYYY.csv          one row per regular-season game (id, date, start UTC, teams, final score, ot/so flag)
  player_games_YYYY.csv   one row per player per game: team, position, toi, goalie shots/saves, goalie `starter` flag
  errors.csv              games that could not be read (with reason)
  samples/                one raw schedule reply and one raw boxscore reply, to confirm field names

Starting goalie rule: use `starter` when the API gives it (newer seasons). Otherwise the first goalie who
played for the team is NOT guaranteed to be the starter (pulled goalies), so also saved: goalie_order (1 = listed first)
and toi, so the analysis can use "most toi" or "listed first" and compare them.
"Who missed" = in the team's previous game's lineup but not in this one. It includes healthy scratches
(the API only lists players who dressed AND played). Treat as a stand-in for injuries, as the live NHL model does.
"""
import csv, json, os, sys, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "nhl"); os.makedirs(os.path.join(OUT, "samples"), exist_ok=True)
API = "https://api-web.nhle.com/v1"


def get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 sports-research"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except Exception as e:
            code = getattr(e, "code", None)
            if code == 404 or k == tries - 1:
                raise
            time.sleep(2 * (k + 1))


def sample(name, obj):
    p = os.path.join(OUT, "samples", name)
    if not os.path.exists(p):
        json.dump(obj, open(p, "w"))


def name_of(x):
    n = x.get("name")
    return n.get("default") if isinstance(n, dict) else (n or "")


def season_games(season):
    """All regular-season games of a season via the weekly schedule endpoint."""
    d = dt.date(season - 1, 9, 20); end = dt.date(season, 4, 30); seen = {}
    while d <= end:
        try:
            w = get(f"{API}/schedule/{d.isoformat()}")
            sample("schedule_sample.json", w)
            for day in w.get("gameWeek", []):
                for g in day.get("games", []):
                    if g.get("gameType") == 2:
                        seen[g["id"]] = g
        except Exception as e:
            print("schedule fail", d, str(e)[:60])
        d += dt.timedelta(days=7)
    return list(seen.values())


def player_rows(box, g):
    rows = []
    pbg = box.get("playerByGameStats") or {}
    for side in ("homeTeam", "awayTeam"):
        team = (box.get(side) or g.get(side) or {}).get("abbrev")
        stats = pbg.get(side) or {}
        for pos_group in ("forwards", "defense"):
            for p in stats.get(pos_group, []) or []:
                rows.append(dict(game_id=g["id"], team=team, home=side == "homeTeam", player_id=p.get("playerId"), name=name_of(p),
                                 position=p.get("position"), toi=p.get("toi"), goals=p.get("goals"), assists=p.get("assists"),
                                 shots=p.get("sog", p.get("shots")), goalie_order="", sa="", saves="", starter=""))
        for i, p in enumerate(stats.get("goalies", []) or [], 1):
            rows.append(dict(game_id=g["id"], team=team, home=side == "homeTeam", player_id=p.get("playerId"), name=name_of(p),
                             position="G", toi=p.get("toi"), goals="", assists="", shots="", goalie_order=i,
                             sa=p.get("shotsAgainst"), saves=p.get("saves"), starter=p.get("starter", "")))
    return rows


def one(g):
    try:
        box = get(f"{API}/gamecenter/{g['id']}/boxscore")
        sample("boxscore_sample.json", box)
        h, a = box.get("homeTeam", {}), box.get("awayTeam", {})
        row = dict(game_id=g["id"], date_et=(g.get("startTimeUTC") or "")[:10], start_utc=g.get("startTimeUTC"), home=h.get("abbrev"), away=a.get("abbrev"),
                   home_score=h.get("score"), away_score=a.get("score"), last_period=(box.get("gameOutcome") or {}).get("lastPeriodType"))
        pr = player_rows(box, g)
        if not pr:
            return None, None, f"{g['id']}: no player rows"
        return row, pr, None
    except Exception as e:
        return None, None, f"{g['id']}: {type(e).__name__} {str(e)[:80]}"


def write(path, rows, cols):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)


def main():
    seasons = [int(x) for x in sys.argv[1:]] or list(range(2011, 2028))
    gcols = ["game_id", "date_et", "start_utc", "home", "away", "home_score", "away_score", "last_period"]
    pcols = ["game_id", "team", "home", "player_id", "name", "position", "toi", "goals", "assists", "shots", "goalie_order", "sa", "saves", "starter"]
    errs = []
    for s in seasons:
        gp, pp = os.path.join(OUT, f"games_{s}.csv"), os.path.join(OUT, f"player_games_{s}.csv")
        have = set(); grows = []; prows = []
        if os.path.exists(gp):
            grows = list(csv.DictReader(open(gp))); have = {int(r["game_id"]) for r in grows}
            prows = list(csv.DictReader(open(pp)))
        sched = season_games(s)
        todo = [g for g in sched if g["id"] not in have and g.get("gameState") in ("OFF", "FINAL")]
        print(f"season {s}: {len(sched)} scheduled, {len(have)} saved, {len(todo)} to fetch", flush=True)
        with ThreadPoolExecutor(4) as ex:
            for row, pr, err in ex.map(one, todo):
                if err: errs.append(dict(season=s, error=err)); continue
                grows.append(row); prows.extend(pr)
        write(gp, grows, gcols); write(pp, prows, pcols)
    if errs:
        write(os.path.join(OUT, "errors.csv"), errs, ["season", "error"])
        print(len(errs), "errors, see nhl/errors.csv")


if __name__ == "__main__":
    main()
