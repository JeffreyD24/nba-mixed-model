"""Job A part 1: one row per player-game (including DNPs) for NBA regular seasons 2011-12 .. 2025-26, from ESPN's public site API
(the same feeds backfill_minutes.py uses; stats.nba.com blocks cloud IPs). Run in GitHub Actions from this folder:
  python fetch_nba_box.py 2012 2013 ...     (season = END year). Safe to rerun: games already in parts/ are skipped.
Writes parts/season_YYYY.csv: season, date (Eastern), game_id (ESPN event id), team (repo code), home, player_id, player, minutes, played, plus_minus, starter."""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.path.insert(0, "../../.."); import espn
os.makedirs("parts", exist_ok=True)
END = {2012: "2012-04-26", 2013: "2013-04-17", 2014: "2014-04-16", 2015: "2015-04-15", 2016: "2016-04-13", 2017: "2017-04-12", 2018: "2018-04-11",
       2019: "2019-04-10", 2020: "2020-08-14", 2021: "2021-05-16", 2022: "2022-04-10", 2023: "2023-04-09", 2024: "2024-04-14",
       2025: "2025-04-13", 2026: "2026-04-12"}

def box(ev, season):
    comp = ev["competitions"][0]; home = {c["team"]["id"]: c["homeAway"] == "home" for c in comp["competitors"]}
    for k in range(4):
        try: s = espn._get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={ev['id']}"); break
        except Exception as e:
            if k == 3: return [], f"{ev['id']}: {type(e).__name__} {str(e)[:60]}"
            time.sleep(4 * (k + 1))
    date = pd.Timestamp(ev["date"]).tz_convert("America/New_York").strftime("%Y-%m-%d"); rows = []
    for tb in s.get("boxscore", {}).get("players", []):
        code = espn.ESPN2.get(tb["team"]["abbreviation"]) or tb["team"]["abbreviation"].lower()
        for st in tb.get("statistics", [])[:1]:
            names = st["names"]
            for a in st["athletes"]:
                ath = a.get("athlete") or {}; vals = a.get("stats") or []
                def g(n):
                    return vals[names.index(n)] if n in names and names.index(n) < len(vals) else None
                m = g("MIN"); m = float(m) if m not in (None, "", "--") else 0.0
                rows.append(dict(season=season, date=date, game_id=str(ev["id"]), team=code, home=int(home.get(tb["team"]["id"], False)),
                                 player_id=ath.get("id") or f"name:{ath.get('displayName')}", player=ath.get("displayName"), minutes=m,
                                 played=int(m > 0 and not a.get("didNotPlay")), plus_minus=g("+/-"), starter=int(bool(a.get("starter")))))
    return rows, None

for season in [int(x) for x in sys.argv[1:]]:
    path = f"parts/season_{season}.csv"
    old = pd.read_csv(path, dtype={"game_id": str}) if os.path.exists(path) else pd.DataFrame()
    done = set(old.game_id) if len(old) else set()
    events = []
    for d in pd.date_range(f"{season - 1}-10-15", END[season]):
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
    print(f"{season}: errors {len(errs)} {errs[:3]}", flush=True)
