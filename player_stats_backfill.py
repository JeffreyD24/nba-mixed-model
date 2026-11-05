"""
Full player box stats per game (ESPN public summary feed) for the player-props model: minutes, points, rebounds (off/def),
assists, threes made/attempted, field goals, free throws, turnovers, steals, blocks, fouls, starter, plus-minus.
Regular seasons 2021-22 .. 2025-26, plus the current season to date (2026-27). Safe to rerun: games already saved are skipped.
  python player_stats_backfill.py WORKDIR 2022 2023 2024 2025 2026 2027
Writes data/player_stats/season_YYYY.csv.gz (season = END year).
"""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
W = os.path.abspath(sys.argv[1]); sys.path.insert(0, W)
import espn
OUT = os.path.join(W, "data", "player_stats"); os.makedirs(OUT, exist_ok=True)
END = {2022: "2022-04-10", 2023: "2023-04-09", 2024: "2024-04-14", 2025: "2025-04-13", 2026: "2026-04-12", 2027: None}


def made_att(v):
    try: a, b = str(v).split("-"); return float(a), float(b)
    except Exception: return float("nan"), float("nan")


def num(v):
    try: return float(v)
    except Exception: return 0.0 if v in ("--", "-", "", None) else float("nan")


def box(ev, season):
    comp = ev["competitions"][0]; home = {c["team"]["id"]: c["homeAway"] == "home" for c in comp["competitors"]}
    for k in range(4):
        try: s = espn._get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={ev['id']}"); break
        except Exception as e:
            if k == 3: return [], f"{ev['id']}: {type(e).__name__}"
            time.sleep(4 * (k + 1))
    date = pd.Timestamp(ev["date"]).tz_convert("America/New_York").strftime("%Y-%m-%d"); rows = []
    for tb in s.get("boxscore", {}).get("players", []):
        code = espn.ESPN2.get(tb["team"]["abbreviation"]) or tb["team"]["abbreviation"].lower()
        for st in tb.get("statistics", [])[:1]:
            names = st["names"]
            for a in st["athletes"]:
                ath = a.get("athlete") or {}; vals = a.get("stats") or []
                g = lambda n: vals[names.index(n)] if n in names and names.index(n) < len(vals) else None
                fgm, fga = made_att(g("FG")); tpm, tpa = made_att(g("3PT")); ftm, fta = made_att(g("FT"))
                m = num(g("MIN")); m = 0.0 if m != m else m
                rows.append(dict(season=season, date=date, game_id=str(ev["id"]), team=code, home=int(home.get(tb["team"]["id"], False)),
                                 player_id=ath.get("id"), player=ath.get("displayName"), starter=int(bool(a.get("starter"))),
                                 dnp=int(bool(a.get("didNotPlay")) or m == 0), min=m, pts=num(g("PTS")), reb=num(g("REB")),
                                 oreb=num(g("OREB")), dreb=num(g("DREB")), ast=num(g("AST")), fg3m=tpm, fg3a=tpa, fgm=fgm, fga=fga,
                                 ftm=ftm, fta=fta, tov=num(g("TO")), stl=num(g("STL")), blk=num(g("BLK")), pf=num(g("PF")),
                                 pm=num(g("+/-"))))
    return rows, None


for season in [int(x) for x in sys.argv[2:]]:
    path = os.path.join(OUT, f"season_{season}.csv.gz")
    old = pd.read_csv(path, dtype={"game_id": str, "player_id": str}) if os.path.exists(path) else pd.DataFrame()
    done = set(old.game_id) if len(old) else set()
    end = END[season] or (pd.Timestamp.now(tz="America/New_York") - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    events = []
    for d in pd.date_range(f"{season - 1}-10-15", end):
        try: sb = espn._get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={d:%Y%m%d}")
        except Exception as e: print("scoreboard failed", d.date(), e); continue
        for ev in sb.get("events", []):
            if ev.get("season", {}).get("type") != 2: continue
            if ev["competitions"][0].get("status", {}).get("type", {}).get("state") != "post": continue
            if str(ev["id"]) not in done: events.append(ev)
    print(f"{season}: {len(done)} games saved, {len(events)} to fetch", flush=True)
    rows, errs, t0 = [], [], time.time()
    with ThreadPoolExecutor(4) as ex:
        for i, (r, e) in enumerate(ex.map(lambda ev: box(ev, season), events), 1):
            rows += r
            if e: errs.append(e)
            if i % 200 == 0: print(f"  {i}/{len(events)} {time.time() - t0:.0f}s", flush=True)
    if rows: pd.concat([old, pd.DataFrame(rows)], ignore_index=True).to_csv(path, index=False)
    print(f"{season}: saved {len(rows)} rows, errors {len(errs)} {errs[:3]}", flush=True)
