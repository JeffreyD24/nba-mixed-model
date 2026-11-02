"""
Live odds recorder (The Odds API, key in the GitHub secret ODDS_API_KEY; never printed or saved): Pinnacle, the sharp book,
plus nine US books, for NBA, NHL and NFL. Runs with every 5-minute line check.
  - research/live_odds/{sport}/{YYYY-MM-DD}.csv.gz  every snapshot (time, game, book, market, outcome, price, point)
  - state/pinnacle_now.json                          latest Pinnacle prices per game, for the NHL "Pinnacle disagrees" note
Cost: 3 credits per sport per call (moneyline, spread, total; up to 10 books count as one region) -> about 2,600 a day.
  python pinnacle_watch.py WORKDIR
"""
import os, sys, json, urllib.request, urllib.parse, urllib.error
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

W = os.path.abspath(sys.argv[1])
KEYS = {"nba": "basketball_nba", "nhl": "icehockey_nhl", "nfl": "americanfootball_nfl"}
BOOKS = "pinnacle,draftkings,fanduel,betmgm,williamhill_us,betrivers,bovada,betonlineag,lowvig,mybookieag"
ET = ZoneInfo("America/New_York")
MIN_CREDITS = 50000                     # stop recording before the plan runs low


def get(sport):
    key = os.environ.get("ODDS_API_KEY")
    if not key: return None, None
    url = f"https://api.the-odds-api.com/v4/sports/{KEYS[sport]}/odds?" + urllib.parse.urlencode(
        dict(apiKey=key, bookmakers=BOOKS, markets="h2h,spreads,totals", oddsFormat="american", dateFormat="iso"))
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read()), int(r.headers.get("x-requests-remaining", 0) or 0)
    except urllib.error.HTTPError as e:
        print(f"{sport}: The Odds API returned HTTP {e.code}"); return None, None
    except Exception as e:
        print(f"{sport}: {type(e).__name__}"); return None, None


def main():
    if not os.environ.get("ODDS_API_KEY"): print("ODDS_API_KEY not set; live odds not recorded."); return
    now = dt.datetime.now(dt.timezone.utc); stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    sp = os.path.join(W, "state", "pinnacle_now.json")
    latest = json.load(open(sp)) if os.path.exists(sp) else {}
    left = None
    for sport in KEYS:
        js, left = get(sport)
        if js is None: continue
        rows = []
        for ev in js:
            ct = pd.Timestamp(ev["commence_time"])
            if ct <= pd.Timestamp(now): continue                     # pre-game only (live in-game lines come from Action Network)
            for bk in ev.get("bookmakers", []):
                for mk in bk.get("markets", []):
                    for o in mk.get("outcomes", []):
                        rows.append(dict(snapshot_utc=stamp, event_id=ev["id"], commence_et=str(ct.tz_convert(ET).tz_localize(None)),
                                         home=ev["home_team"], away=ev["away_team"], book=bk["key"], market=mk["key"],
                                         outcome=o.get("name"), price=o.get("price"), point=o.get("point"),
                                         book_last_update=mk.get("last_update")))
                        if bk["key"] == "pinnacle":
                            g = latest.setdefault(sport, {}).setdefault(ev["id"], dict(home=ev["home_team"], away=ev["away_team"],
                                                                                  commence_et=str(ct.tz_convert(ET).tz_localize(None))))
                            g.setdefault("first_seen_utc", stamp); g["updated_utc"] = stamp
                            g[f"{mk['key']}|{o.get('name')}"] = [o.get("price"), o.get("point")]
                            g.setdefault("first", {}).setdefault(f"{mk['key']}|{o.get('name')}", [o.get("price"), o.get("point")])
        if rows:
            day = now.astimezone(ET).strftime("%Y-%m-%d")
            d = os.path.join(W, "research", "live_odds", sport); os.makedirs(d, exist_ok=True)
            p = os.path.join(d, f"{day}.csv.gz")
            new = pd.DataFrame(rows)
            if os.path.exists(p): new = pd.concat([pd.read_csv(p), new], ignore_index=True)
            new.to_csv(p, index=False, compression="gzip")
        print(f"{sport}: {len(js)} games, {len(rows)} prices recorded")
    # forget games that started more than a day ago
    cut = (pd.Timestamp(now.astimezone(ET)).tz_localize(None) - pd.Timedelta(days=1))
    for sport in list(latest):
        latest[sport] = {k: v for k, v in latest[sport].items() if pd.Timestamp(v["commence_et"]) > cut}
    json.dump(latest, open(sp, "w"))
    if left is not None:
        print(f"credits left: {left:,}")
        if left < MIN_CREDITS: open(os.path.join(W, "state", "pinnacle_off"), "w").write(stamp)


if __name__ == "__main__":
    if os.path.exists(os.path.join(W, "state", "pinnacle_off")): print("Live odds recorder paused (credits low)."); sys.exit(0)
    main()
