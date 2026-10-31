"""
Backfill who-played-when (minutes by quarter) for past regular seasons from ESPN play-by-play.

python backfill_minutes.py WORKDIR 2022 2023 ...   (season = the year it ends; 2022 = 2021-22)
Writes research/minutes_history/season_YYYY.csv. Safe to rerun: games already saved are skipped.
Dates come from data/training_games.csv. Uses 4 requests at a time.
"""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import espn, rotations

W = os.path.abspath(sys.argv[1]); SEASONS = [int(x) for x in sys.argv[2:]]
OUT = os.path.join(W, "research", "minutes_history"); os.makedirs(OUT, exist_ok=True)
G = pd.read_csv(os.path.join(W, "data", "training_games.csv"))


def one(ev, season):
    comp = ev["competitions"][0]
    side = {c["homeAway"]: espn.ESPN2.get(c["team"]["abbreviation"]) for c in comp["competitors"]}
    for k in range(3):
        try:
            rows, worst = rotations.game_minutes(ev["id"]); break
        except Exception as e:
            if k == 2: return [], f"{ev['id']}: {type(e).__name__} {str(e)[:80]}"
            time.sleep(5 * (k + 1))
    for r in rows:
        r.update(season=season, espn_event_id=str(ev["id"]), date=pd.Timestamp(ev["date"]).tz_convert("America/New_York").strftime("%Y-%m-%d"),
                 home=side.get("home"), away=side.get("away"), is_home=r["team"] == side.get("home"), check_max_diff_min=worst)
    return rows, None


for season in SEASONS:
    path = os.path.join(OUT, f"season_{season}.csv")
    old = pd.read_csv(path, dtype={"espn_event_id": str}) if os.path.exists(path) else pd.DataFrame()
    done = set(old.espn_event_id) if len(old) else set()
    dates = sorted(G[G.season == season].date.unique())
    events = []
    for d in dates:
        try:
            sb = espn._get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={pd.Timestamp(d):%Y%m%d}")
        except Exception as e:
            print("scoreboard failed", d, e); continue
        for ev in sb.get("events", []):
            if ev.get("season", {}).get("type") not in (None, 2): continue          # regular season only
            if ev["competitions"][0].get("status", {}).get("type", {}).get("state") != "post": continue
            if str(ev["id"]) not in done: events.append(ev)
    print(f"{season}: {len(dates)} dates, {len(done)} games already saved, {len(events)} to do", flush=True)
    rows, errs, t0 = [], [], time.time()
    with ThreadPoolExecutor(4) as ex:
        for i, (r, e) in enumerate(ex.map(lambda ev: one(ev, season), events), 1):
            rows += r
            if e: errs.append(e)
            if i % 200 == 0: print(f"  {i}/{len(events)} games, {time.time() - t0:.0f}s", flush=True)
    if rows:
        new = pd.DataFrame(rows)
        front = ["season", "espn_event_id", "date", "away", "home", "team", "is_home", "athlete_id", "player", "starter", "dnp",
                 "q1", "q2", "q3", "q4", "h1", "h2", "total_min", "box_min", "diff_vs_box", "check_max_diff_min"]
        new = new[[c for c in front if c in new] + [c for c in new if c not in front]]
        pd.concat([old, new], ignore_index=True).to_csv(path, index=False)
    allg = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    if len(allg):
        g = allg.groupby("espn_event_id").check_max_diff_min.first()
        print(f"{season}: saved {g.size} games; within 1 minute of the box score: {(g <= 1).mean():.0%}; errors: {len(errs)}", flush=True)
    for e in errs[:20]: print("  error", e)
